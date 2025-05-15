import os
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import threading
import queue

class RenderStatus(Enum):
    """Status of a frame render"""
    PENDING = "pending"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class FrameInfo:
    """Information about a frame's render status"""
    frame: int
    status: RenderStatus
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None

class RenderManager:
    """Manages the rendering process for Houdini files"""

    def __init__(self, hip_file: str, out_node: str, frame_range: Tuple[int, int], frame_complete_callback=None):
        self.hip_file = hip_file
        self.out_node = out_node
        self.frame_range = frame_range
        self.frame_info: Dict[int, FrameInfo] = {}
        self.render_queue: queue.Queue = queue.Queue()
        self.status_queue: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_threads: List[threading.Thread] = []
        self.frame_complete_callback = frame_complete_callback

        # Initialize frame info
        for frame in range(frame_range[0], frame_range[1] + 1):
            self.frame_info[frame] = FrameInfo(frame=frame, status=RenderStatus.PENDING)

    def start_rendering(self, num_threads: int = 1) -> None:
        """Start the rendering process with the specified number of threads"""
        # Clear any existing state
        self.stop_event.clear()
        self.render_queue.queue.clear()
        self.status_queue.queue.clear()

        # Add frames to queue
        for frame in range(self.frame_range[0], self.frame_range[1] + 1):
            self.render_queue.put(frame)

        # Start worker threads
        self.worker_threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=self._render_worker)
            thread.daemon = True
            thread.start()
            self.worker_threads.append(thread)

    def stop_rendering(self) -> None:
        """Stop the rendering process"""
        self.stop_event.set()
        for thread in self.worker_threads:
            thread.join()
        self.worker_threads.clear()

    def _render_worker(self) -> None:
        """Worker thread that processes frames from the queue"""
        while not self.stop_event.is_set():
            try:
                frame = self.render_queue.get_nowait()
            except queue.Empty:
                break

            self._render_frame(frame)
            self.render_queue.task_done()

    def _render_frame(self, frame: int) -> None:
        """Render a single frame"""
        frame_info = self.frame_info[frame]
        frame_info.status = RenderStatus.RENDERING
        frame_info.start_time = time.time()

        # Check if frame is already rendered
        output_file = self._get_output_file(frame)
        if output_file and output_file.exists():
            frame_info.status = RenderStatus.COMPLETED
            frame_info.end_time = time.time()
            self.status_queue.put(frame_info)
            if self.frame_complete_callback:
                self.frame_complete_callback(str(output_file))
            return

        # Build render command
        cmd = [
            "hython",
            "-c",
            f"""
import hou
hou.hipFile.load(r"{self.hip_file}")
node = hou.node(r"{self.out_node}")
node.render(frame_range=({frame}, {frame}))
"""
        ]

        try:
            # Run render command
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self._get_render_env()
            )

            if process.returncode == 0:
                frame_info.status = RenderStatus.COMPLETED
            else:
                frame_info.status = RenderStatus.FAILED
                frame_info.error = process.stderr

        except Exception as e:
            frame_info.status = RenderStatus.FAILED
            frame_info.error = str(e)

        frame_info.end_time = time.time()
        self.status_queue.put(frame_info)
        if self.frame_complete_callback and frame_info.status == RenderStatus.COMPLETED:
            output_file = self._get_output_file(frame)
            if output_file and output_file.exists():
                self.frame_complete_callback(str(output_file))

    def _get_output_file(self, frame: int) -> Optional[Path]:
        """Get the output file path for a frame"""
        try:
            import hou
            hou.hipFile.load(self.hip_file)
            node = hou.node(self.out_node)
            if node:
                return Path(node.evalParm("sopoutput") or node.evalParm("RS_outputFileNamePrefix"))
        except ImportError:
            # If we can't import hou, try to guess the output path
            base_dir = Path(self.hip_file).parent
            return base_dir / f"render_{frame:04d}.exr"
        return None

    def _get_render_env(self) -> Dict[str, str]:
        """Get environment variables for rendering"""
        env = os.environ.copy()
        env["HOU_VERBOSITY"] = "0"
        env["RS_VERBOSITY_LEVEL"] = "0"
        return env

    def get_frame_status(self, frame: int) -> FrameInfo:
        """Get the status of a specific frame"""
        return self.frame_info[frame]

    def get_all_frame_status(self) -> Dict[int, FrameInfo]:
        """Get the status of all frames"""
        return self.frame_info.copy()

    def get_progress(self) -> Tuple[int, int]:
        """Get the number of completed frames and total frames"""
        completed = sum(1 for info in self.frame_info.values()
                       if info.status in [RenderStatus.COMPLETED, RenderStatus.SKIPPED])
        total = len(self.frame_info)
        return completed, total

    def get_remaining_time(self) -> Optional[float]:
        """Estimate remaining render time based on completed frames"""
        completed_frames = [info for info in self.frame_info.values()
                          if info.status == RenderStatus.COMPLETED
                          and info.start_time is not None
                          and info.end_time is not None]

        if not completed_frames:
            return None

        # Calculate average time per frame
        avg_time = sum(info.end_time - info.start_time for info in completed_frames) / len(completed_frames)

        # Calculate remaining frames
        remaining = sum(1 for info in self.frame_info.values()
                       if info.status not in [RenderStatus.COMPLETED, RenderStatus.SKIPPED])

        return avg_time * remaining
