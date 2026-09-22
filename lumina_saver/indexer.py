import os
import sqlite3
import random
import time
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Generator

class MediaIndexer:
    """SQLite-backed high-performance media scanner and random selector for 60k+ items."""

    def __init__(self, db_path: str, media_dirs: List[str], image_exts: List[str], video_exts: List[str]):
        self.db_path = db_path
        self.media_dirs = [os.path.abspath(d) for d in media_dirs]
        self.image_exts = set(ext.lower() for ext in image_exts)
        self.video_exts = set(ext.lower() for ext in video_exts)
        
        self._ensure_db_dir()
        self._init_db()
        
        self.history_stack: List[Dict[str, Any]] = []
        self.history_index: int = -1

    def _ensure_db_dir(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def close(self):
        """Closes any background handles and releases database locks."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conn.close()
        except Exception:
            pass

    def _init_db(self):
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS media_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    folder_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    width INTEGER DEFAULT 0,
                    height INTEGER DEFAULT 0,
                    date_taken TEXT,
                    last_shown REAL DEFAULT 0,
                    show_count INTEGER DEFAULT 0
                );
            """)
            # Migration check for existing DBs
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(media_files);").fetchall()]
            if "width" not in cols:
                conn.execute("ALTER TABLE media_files ADD COLUMN width INTEGER DEFAULT 0;")
            if "height" not in cols:
                conn.execute("ALTER TABLE media_files ADD COLUMN height INTEGER DEFAULT 0;")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_folder ON media_files(folder_path);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_media_type ON media_files(media_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_shown ON media_files(last_shown);")

    def _batch_insert(self, files: List[Tuple[str, str, str, str, str, int, float, int, int]]):
        if not files:
            return
        with self.get_connection() as conn:
            conn.executemany("""
                INSERT INTO media_files (file_path, folder_path, file_name, media_type, extension, file_size, mtime, width, height)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_size=excluded.file_size,
                    mtime=excluded.mtime,
                    width=CASE WHEN excluded.width > 0 THEN excluded.width ELSE media_files.width END,
                    height=CASE WHEN excluded.height > 0 THEN excluded.height ELSE media_files.height END;
            """, files)
            conn.commit()

    def scan_directories(self, progress_callback=None, inspect_dimensions: bool = False) -> int:
        """Asynchronously scan configured directories and sync with SQLite DB."""
        import warnings
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)

        found_files: List[Tuple[str, str, str, str, str, int, float, int, int]] = []
        start_time = time.time()
        count = 0
        batch_size = 500

        # Pre-load existing file cache (path -> (size, mtime))
        existing_cache: Dict[str, Tuple[int, float]] = {}
        with self.get_connection() as conn:
            rows = conn.execute("SELECT file_path, file_size, mtime FROM media_files;").fetchall()
            for r in rows:
                existing_cache[r["file_path"]] = (r["file_size"], r["mtime"])

        for root_dir in self.media_dirs:
            if not os.path.exists(root_dir):
                try:
                    os.makedirs(root_dir, exist_ok=True)
                    print(f"[Indexer] Created default directory: {root_dir}")
                except Exception as e:
                    print(f"[Indexer] Warning: Could not create or access directory {root_dir}: {e}")
                    continue

            print(f"[Indexer] Scanning: {root_dir}")
            for dirpath, _, filenames in os.walk(root_dir):
                for fname in filenames:
                    ext = os.path.splitext(fname)[1].lower()
                    media_type = None
                    if ext in self.image_exts:
                        media_type = "image"
                    elif ext in self.video_exts:
                        media_type = "video"

                    fname_lower = fname.lower()
                    dirpath_lower = dirpath.lower()
                    if any(t in fname_lower or t in dirpath_lower for t in ["thumbnail", "_thumb.", ".thumb", "thumbs.db", "albumart", ".cache"]):
                        continue

                    if media_type:
                        full_path = os.path.join(dirpath, fname)
                        try:
                            st = os.stat(full_path)
                            size, mtime = st.st_size, st.st_mtime

                            # Fast incremental check: if file size & mtime match cache, skip image header parse
                            if full_path in existing_cache:
                                cached_size, cached_mtime = existing_cache[full_path]
                                if cached_size == size and abs(cached_mtime - mtime) < 0.01:
                                    count += 1
                                    continue

                            w, h = 0, 0
                            # Only open image if deep dimension inspection is explicitly requested
                            if inspect_dimensions and media_type == "image":
                                try:
                                    with Image.open(full_path) as img:
                                        w, h = img.width, img.height
                                except Exception:
                                    pass

                            found_files.append((
                                full_path,
                                dirpath,
                                fname,
                                media_type,
                                ext,
                                size,
                                mtime,
                                w,
                                h
                            ))
                            count += 1

                            if len(found_files) >= batch_size:
                                self._batch_insert(found_files)
                                found_files.clear()
                                if progress_callback:
                                    progress_callback(count)

                        except OSError:
                            continue

        # Final batch insert
        if found_files:
            self._batch_insert(found_files)
            found_files.clear()

        print(f"[Indexer] Scan finished: {count} media files processed in {time.time() - start_time:.2f}s")
        
        # Clean up stale files or files from unconfigured directories
        self._purge_stale_files()
        return self.get_total_count()

    def update_media_dimensions(self, media_id: int, width: int, height: int):
        """Updates photo dimensions in SQLite when decoded or inspected."""
        if not media_id or (width <= 0 and height <= 0):
            return
        try:
            with self.get_connection() as conn:
                conn.execute("UPDATE media_files SET width = ?, height = ? WHERE id = ?;", (width, height, media_id))
                conn.commit()
        except Exception:
            pass

    def populate_unindexed_dimensions(self, batch_size: int = 50) -> int:
        """Inspects dimensions for a batch of unindexed images (width = 0) in SQLite.
        Returns the number of files inspected in this batch.
        """
        from lumina_saver.exif_reader import ExifReader
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, file_path FROM media_files WHERE media_type = 'image' AND width = 0 LIMIT ?;",
                (batch_size,)
            ).fetchall()
            if not rows:
                return 0

            updates = []
            for row in rows:
                w, h = ExifReader.get_image_dimensions(row["file_path"])
                if w > 0 and h > 0:
                    updates.append((w, h, row["id"]))

            if updates:
                conn.executemany("UPDATE media_files SET width = ?, height = ? WHERE id = ?;", updates)
                conn.commit()
            return len(rows)

    def _purge_stale_files(self):
        with self.get_connection() as conn:
            rows = conn.execute("SELECT id, file_path FROM media_files").fetchall()
            stale_ids = []
            for row in rows:
                path = os.path.abspath(row["file_path"])
                exists = os.path.exists(path)
                in_active_dirs = any(path.startswith(d) for d in self.media_dirs)
                if not exists or not in_active_dirs:
                    stale_ids.append(row["id"])

            if stale_ids:
                conn.executemany("DELETE FROM media_files WHERE id = ?", [(i,) for i in stale_ids])
                conn.commit()
                print(f"[Indexer] Purged {len(stale_ids)} unconfigured or deleted files from index.")

    def _build_filter_sql(self, min_res: str = "none", orientation: str = "all", skip_folder: Optional[str] = None) -> Tuple[str, List[Any]]:
        where_clauses = []
        params = []

        if skip_folder:
            where_clauses.append("folder_path != ?")
            params.append(skip_folder)

        # Resolution filtering
        if min_res == "720p":
            where_clauses.append("(width >= 1280 OR height >= 1280 OR width = 0 OR media_type = 'video')")
        elif min_res == "1080p":
            where_clauses.append("(width >= 1920 OR height >= 1920 OR width = 0 OR media_type = 'video')")
        elif min_res == "4k":
            where_clauses.append("(width >= 3840 OR height >= 3840 OR width = 0 OR media_type = 'video')")

        # Orientation filtering
        if orientation == "landscape":
            where_clauses.append("((width >= height AND width > 0) OR width = 0 OR (media_type = 'video' AND (width >= height OR width = 0)))")
        elif orientation == "portrait":
            where_clauses.append("((height > width AND height > 0) OR width = 0 OR (media_type = 'video' AND (height > width OR width = 0)))")

        where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        return where_str, params

    def get_total_count(self, min_res: str = "none", orientation: str = "all") -> int:
        where_str, params = self._build_filter_sql(min_res, orientation)
        with self.get_connection() as conn:
            res = conn.execute(f"SELECT COUNT(*) as total FROM media_files{where_str};", params).fetchone()
            return res["total"] if res else 0

    def get_next_media(
        self, 
        min_res: str = "none", 
        orientation: str = "all", 
        display_order: str = "random", 
        last_id: int = 0,
        skip_folder: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Returns next media file matching filters, handling random or sequential resume order."""
        from lumina_saver.exif_reader import ExifReader

        total = self.get_total_count(min_res, orientation)
        if total == 0:
            return None

        # Check if navigating forward in history stack
        if self.history_index < len(self.history_stack) - 1:
            self.history_index += 1
            return self.history_stack[self.history_index]

        def matches_filters(cand: Dict[str, Any]) -> bool:
            w, h = cand.get("width", 0), cand.get("height", 0)
            mtype = cand.get("media_type", "image")
            if mtype == "image":
                if orientation == "landscape" and w > 0 and h > 0 and w < h:
                    return False
                if orientation == "portrait" and w > 0 and h > 0 and h <= w:
                    return False
                max_d = max(w, h)
                if min_res == "720p" and max_d > 0 and max_d < 1280:
                    return False
                if min_res == "1080p" and max_d > 0 and max_d < 1920:
                    return False
                if min_res == "4k" and max_d > 0 and max_d < 3840:
                    return False
            elif mtype == "video":
                if orientation == "landscape" and w > 0 and h > 0 and w < h:
                    return False
                if orientation == "portrait" and w > 0 and h > 0 and h <= w:
                    return False
            return True

        def inspect_candidate(cand: Dict[str, Any], conn) -> bool:
            if cand.get("media_type") == "image" and cand.get("width", 0) <= 0:
                w, h = ExifReader.get_image_dimensions(cand["file_path"])
                if w > 0 and h > 0:
                    cand["width"] = w
                    cand["height"] = h
                    try:
                        conn.execute("UPDATE media_files SET width = ?, height = ? WHERE id = ?", (w, h, cand["id"]))
                        conn.commit()
                    except Exception:
                        pass
            return matches_filters(cand)

        where_str, params = self._build_filter_sql(min_res, orientation, skip_folder)
        selected = None

        with self.get_connection() as conn:
            if display_order == "sequential":
                current_last_id = last_id
                max_attempts = 100
                for _ in range(max_attempts):
                    seq_where = where_str + (" AND " if where_str else " WHERE ") + "id > ?"
                    seq_params = params + [current_last_id]
                    row = conn.execute(f"SELECT * FROM media_files{seq_where} ORDER BY id ASC LIMIT 1;", seq_params).fetchone()

                    if not row:
                        # Wrap around to beginning of collection
                        row = conn.execute(f"SELECT * FROM media_files{where_str} ORDER BY id ASC LIMIT 1;", params).fetchone()

                    if not row:
                        break

                    cand = dict(row)
                    if inspect_candidate(cand, conn):
                        selected = cand
                        break
                    else:
                        current_last_id = cand["id"]
            else:
                # Random / Least recently shown mode
                max_batches = 5
                for _ in range(max_batches):
                    query = f"SELECT * FROM media_files{where_str} ORDER BY last_shown ASC, RANDOM() LIMIT 50;"
                    rows = conn.execute(query, params).fetchall()
                    if not rows and skip_folder:
                        fallback_where, fallback_params = self._build_filter_sql(min_res, orientation)
                        rows = conn.execute(f"SELECT * FROM media_files{fallback_where} ORDER BY RANDOM() LIMIT 20;", fallback_params).fetchall()

                    if not rows:
                        break

                    cand_list = [dict(r) for r in rows]
                    random.shuffle(cand_list)
                    for cand in cand_list:
                        if inspect_candidate(cand, conn):
                            selected = cand
                            break

                    if selected:
                        break

            if not selected:
                return None

            # Update last_shown and show_count
            now = time.time()
            conn.execute("UPDATE media_files SET last_shown = ?, show_count = show_count + 1 WHERE id = ?", (now, selected["id"]))
            conn.commit()

        # Counter calculation that cleanly wraps from 1 to total
        seq_idx = ((self.history_index + 1) % total) + 1
        selected["total_count"] = total
        selected["display_index"] = seq_idx

        # Append to history stack
        self.history_stack.append(selected)
        self.history_index = len(self.history_stack) - 1

        if len(self.history_stack) > 500:
            self.history_stack.pop(0)
            self.history_index -= 1

        return selected

    def get_previous_media(self) -> Optional[Dict[str, Any]]:
        """Navigate backwards in the history stack."""
        if self.history_index > 0:
            self.history_index -= 1
            return self.history_stack[self.history_index]
        return self.history_stack[0] if self.history_stack else None
