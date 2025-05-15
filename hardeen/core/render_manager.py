import os
import signal
import subprocess
import threading
import time
import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable, Any

class RenderManager:
    """Manages the rendering process for Houdini files"""

    def __init__(self):
        self.process = None
        self.render_thread = None
        self.canceling = False
        self.killed = False
        self.render_start_time = None
        self._initial_frame_total = 0

        # Callback to update UI
        self.output_callback = None
        self.raw_output_callback = None
        self.progress_callback = None
        self.frame_progress_callback = None
        self.frame_completed_callback = None
        self.frame_skipped_callback = None
        self.image_update_callback = None
        self.render_finished_callback = None
        self.time_labels_callback = None

    def register_callbacks(self,
                          output_callback: Callable[[str, Optional[str], bool, bool], None] = None,
                          raw_output_callback: Callable[[str], None] = None,
                          progress_callback: Callable[[int, int], None] = None,
                          frame_progress_callback: Callable[[int, int], None] = None,
                          frame_completed_callback: Callable[[int, float], None] = None,
                          frame_skipped_callback: Callable[[int], None] = None,
                          image_update_callback: Callable[[str], None] = None,
                          render_finished_callback: Callable[[], None] = None,
                          time_labels_callback: Callable[[float, float, float, float, datetime.datetime, bool], None] = None):
        """Register callbacks for updating the UI"""
        self.output_callback = output_callback
        self.raw_output_callback = raw_output_callback
        self.progress_callback = progress_callback
        self.frame_progress_callback = frame_progress_callback
        self.frame_completed_callback = frame_completed_callback
        self.frame_skipped_callback = frame_skipped_callback
        self.image_update_callback = image_update_callback
        self.render_finished_callback = render_finished_callback
        self.time_labels_callback = time_labels_callback

    def create_temp_python_file(self):
        """Create the temporary Python file for Houdini"""
        dir_path = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.abspath(os.path.join(dir_path, '../..'))
        temp_file = os.path.join(parent_dir, 'hardeen_temp.py')

        if os.path.exists(temp_file):
            os.remove(temp_file)

        with open(temp_file, 'w') as f:
            f.write('''#!/usr/bin/env python3

import os
import stat
import signal
import sys
from optparse import OptionParser

# Global flag to indicate if we should stop rendering
STOP_RENDERING = False

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    global STOP_RENDERING
    if sig == signal.SIGUSR1:
        print("Received interrupt signal. Will stop after current frame completes.")
        STOP_RENDERING = True
    elif sig == signal.SIGTERM:
        print("Received termination signal. Exiting.")
        sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGUSR1, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def initRender(out, sframe, eframe, userange, useskip, step=1):
    global STOP_RENDERING
    import hou
    rnode = hou.node(out)

    # Set Redshift log verbosity for Alfred-style progress
    if rnode.parm('prerender') is not None:
        rnode.parm('prerender').set('Redshift_setLogLevel -L 5')

    def dataHelper(rop_node, render_event_type, frame):
        if render_event_type == hou.ropRenderEventType.PostFrame:
            output_file = rnode.evalParm("RS_outputFileNamePrefix")
            print(f"hardeen_outputfile: {output_file}")

    rnode.addRenderEventCallback(dataHelper)

    parm_skip = rnode.parm("RS_outputSkipRendered")
    if parm_skip is not None:
        # Convert useskip string to boolean
        skip_enabled = useskip.lower() == "true"
        if skip_enabled:
            parm_skip.set(1)
        else:
            parm_skip.set(0)

    if "merge" in str(rnode.type()).lower():
        rnode.render()
        if userange == "True":
            print("hardeen_note: Out Path leads to a merge node, but you have selected to override the frame range. "
                  "Defaulting to the frame range that was set from within Houdini for each ROP.")
    else:
        if userange == "True":
            # Create a list of frames to render based on step
            frames = list(range(int(sframe), int(eframe) + 1, int(step)))

            # Set the frame range parameters to match our actual frame list
            rnode.parm("f1").set(frames[0])  # First frame in our list
            rnode.parm("f2").set(frames[-1])  # Last frame in our list
            rnode.parm("f3").set(int(step))  # Set frame step

            # Render each frame individually to ensure proper stepping
            for frame in frames:
                # Check if we should stop rendering
                if STOP_RENDERING:
                    print("Interrupt detected - stopping render after current frame.")
                    break

                rnode.render(frame_range=(frame, frame))
        else:
            rnode.render(frame_range=(rnode.parm("f1").eval(), rnode.parm("f2").eval()))

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-i", "--hip", dest="hipfile", help="path to .hip file")
    parser.add_option("-o", "--out", dest="outnode", help="path to out node")
    parser.add_option("-s", "--sframe", dest="startframe", help="start frame to render")
    parser.add_option("-e", "--eframe", dest="endframe", help="end frame to render")
    parser.add_option("-u", "--userange", dest="userange", help="toggle to enable frame range")
    parser.add_option("-r", "--useskip", dest="useskip", help="toggle to skip rendering of already rendered frames")
    parser.add_option("-t", "--step", dest="step", help="render every Nth frame", default="1")

    (options, args) = parser.parse_args()

    # Convert hip file path to absolute and verify it exists
    hip_file = os.path.abspath(options.hipfile.strip())  # Strip whitespace and newlines
    hip_dir = os.path.dirname(hip_file)

    print(f"Current working directory: {os.getcwd()}")
    print(f"Hip file path: {hip_file}")
    print(f"Hip directory: {hip_dir}")

    # Detailed file checks
    exists = os.path.exists(hip_file)
    print(f"File exists: {exists}")

    if exists:
        st = os.stat(hip_file)
        print(f"File mode: {stat.filemode(st.st_mode)}")
        print(f"File owner: {st.st_uid}")
        print(f"File group: {st.st_gid}")
        print(f"File size: {st.st_size}")
    else:
        print("Checking parent directory...")
        parent_dir = os.path.dirname(hip_file)
        if os.path.exists(parent_dir):
            print(f"Parent directory exists")
            try:
                files = os.listdir(parent_dir)
                print(f"Directory contents: {files}")
            except Exception as e:
                print(f"Error listing directory: {e}")
        else:
            print(f"Parent directory does not exist")

    print(f"File is readable: {os.access(hip_file, os.R_OK)}")
    print(f"Current user ID: {os.getuid()}")
    print(f"Current group ID: {os.getgid()}")

    try:
        with open(hip_file, 'rb') as f:
            print("Successfully opened file for reading")
            print(f"First few bytes: {f.read(10)}")
    except Exception as e:
        print(f"Error opening file: {e}")

    # Change to the hip file directory before loading
    os.chdir(hip_dir)

    import hou
    hou.hipFile.load(hip_file)

    initRender(options.outnode.strip(),  # Strip other arguments too
              int(options.startframe),
              int(options.endframe),
              options.userange,
              options.useskip,
              int(options.step))
''')
        return temp_file

    def start_render(self, hip_path: str, out_path: str, start_frame: int, end_frame: int,
                    use_range: bool, use_skip: bool, frame_step: int = 1):
        """Start the render process"""
        if self.process:
            return False  # Already rendering

        self.canceling = False
        self.killed = False
        self.render_start_time = datetime.datetime.now()

        # Calculate frame_total if use_range is True
        frame_total = 0
        if use_range:
            frame_total = len(range(start_frame, end_frame + 1, frame_step))
            if self.progress_callback:
                self.progress_callback(0, frame_total)

        # Create the temp Python file
        temp_file = self.create_temp_python_file()

        # Build command list
        cmd = [
            'hython',
            temp_file,
            '-i', hip_path,
            '-o', out_path,
            '-s', str(start_frame),
            '-e', str(end_frame),
            '-u', str(use_range),
            '-r', str(use_skip),
            '-t', str(frame_step)
        ]

        # Start process
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

        # Emit starting message
        if self.output_callback:
            self.output_callback(
                '\n\n RENDER STARTED AT ' +
                time.strftime('%l:%M%p %Z on %b %d, %Y ') +
                '\n\n',
                color='#22adf2',
                bold=True,
                center=True
            )
            # Change command color to orange and add a line break after it
            self.output_callback(' '.join(cmd) + '\n\n', color='#ff6b2b')
            self.output_callback('Loading scene...\n', color='#c0c0c0')

        # Start monitoring thread with frame_total as initial value
        self._initial_frame_total = frame_total
        self.render_thread = threading.Thread(
            target=self._monitor_render,
            daemon=True
        )
        self.render_thread.start()

        return True

    def interrupt_render(self):
        """Interrupt the render process (graceful stop)"""
        if not self.process or self.canceling:
            return False

        self.canceling = True

        if self.output_callback:
            self.output_callback(
                '\n Interrupt requested... Current frame will finish before stopping. \n\n',
                color='#ff7a7a',
                bold=True,
                center=True
            )

        # Send SIGUSR1 signal to indicate graceful shutdown
        try:
            os.kill(self.process.pid, signal.SIGUSR1)
        except (AttributeError, ProcessLookupError):
            # Fallback to SIGTERM if SIGUSR1 fails
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except (AttributeError, ProcessLookupError):
                pass  # Process might be gone already

        return True

    def kill_render(self):
        """Forcefully kill the render process"""
        if not self.process or self.killed:
            return False

        self.killed = True

        if self.output_callback:
            self.output_callback(
                '\n Force kill requested... Stopping render immediately. \n\n',
                color='#ff7a7a',
                bold=True,
                center=True
            )

        # Send SIGKILL to immediately terminate process
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            self.process.wait()
        except (AttributeError, ProcessLookupError):
            pass  # Process might be gone already

        if self.output_callback:
            self.output_callback(
                '\n Render Killed \n\n',
                color='#ff7a7a',
                bold=True,
                center=True
            )

        # Signal render finished to clean up UI
        if self.render_finished_callback:
            self.render_finished_callback()

        return True

    def _monitor_render(self):
        """Monitor the render process and emit signals as needed"""
        import re
        import select

        try:
            # Initialize variables for tracking render progress
            frame_times = []
            frame_total = self._initial_frame_total  # Start with the initial frame total passed from start_render
            frame_count = 0
            average = 0.0
            recent_average = 0.0
            remaining_time = 0.0
            total_time = 0.0
            current_frame_in_progress = False
            graceful_shutdown_requested = False
            current_frame_start_time = None
            last_eta_time = None
            # Set this to True if we have a valid frame total from arguments to prevent overriding it
            frame_total_from_args = frame_total > 0

            start_time = datetime.datetime.now()
            current_frame_start = None
            current_frame = 0
            current_frame_number = None
            last_update_time = start_time

            # Timer to update elapsed time even when no frames have completed
            last_time_update = datetime.datetime.now()

            # Initialize variables for tracking frames
            frames_seen = set()
            skipped_frames = set()
            consecutive_skips = []

            # Dictionary to track frame render start times
            frame_start_times = {}

            # Variables for block tracking
            completed_blocks = set()
            total_blocks = None
            last_message_type = None

            # Do an initial time update to show "0/0" as frame count and 0s for times
            if self.progress_callback:
                # Initialize with 0 for current frame and the frame_total (or at least 1 if it's 0)
                # This ensures frames display shows "0 / N" at minimum instead of "- / -"
                self.progress_callback(0, max(1, frame_total))

            # Initial time labels with empty values
            if self.time_labels_callback:
                current_time = datetime.datetime.now()
                self.time_labels_callback(
                    0.0,                # Initial elapsed time
                    0.0,                # Initial average
                    0.0,                # Initial total time
                    0.0,                # Initial remaining time
                    current_time,       # Current time as ETA
                    False               # Don't show ETA yet
                )

            while self.process and self.process.poll() is None:
                # Add timeout to readline to allow checking cancellation
                ready = select.select([self.process.stdout], [], [], 0.1)[0]

                # Check if we need to update elapsed time (every 500ms)
                current_time = datetime.datetime.now()
                time_since_update = (current_time - last_time_update).total_seconds()

                if time_since_update >= 0.5:  # Update every half second
                    elapsed_time = (current_time - start_time).total_seconds()

                    # Calculate estimated total based on current progress
                    if frame_total > 0:
                        if average > 0:
                            # If we have frame times, use the average × total frames
                            remaining_frames = max(0, frame_total - frame_count)
                            remaining_time = remaining_frames * average
                            est_total_time = elapsed_time + remaining_time
                        elif frame_count > 0:
                            # If we have started rendering but don't have a good average yet,
                            # use current pace (elapsed ÷ frames done) × total frames
                            current_pace = elapsed_time / frame_count
                            est_total_time = current_pace * frame_total
                            remaining_time = est_total_time - elapsed_time
                        else:
                            # At the very beginning, project based on elapsed time × total frames
                            # Use a simple expanding estimate during initial loading
                            seconds_per_frame_guess = max(0.5, elapsed_time / 10)  # Assume some minimal time per frame
                            est_total_time = seconds_per_frame_guess * frame_total
                            remaining_time = est_total_time - elapsed_time
                    else:
                        # If frame_total is not known yet, just use elapsed time as minimum
                        est_total_time = elapsed_time
                        remaining_time = 0.0

                    # Always ensure remaining time is not negative
                    remaining_time = max(0.0, remaining_time)

                    # Calculate ETA - always show if we have frame_total
                    if frame_total > 0:
                        eta_time = current_time + datetime.timedelta(seconds=remaining_time)
                        show_eta = True
                        last_eta_time = eta_time  # Store valid ETA
                    elif last_eta_time is not None:
                        # If we had a valid ETA before, keep using it
                        eta_time = last_eta_time
                        show_eta = True
                    else:
                        eta_time = current_time
                        show_eta = False

                    # Update time labels with current elapsed time and estimates
                    if self.time_labels_callback:
                        self.time_labels_callback(
                            elapsed_time,   # Current elapsed time (always ticking)
                            average,        # Current average frame time
                            est_total_time, # Current estimated total time
                            remaining_time, # Current remaining time
                            eta_time,       # Current ETA
                            show_eta        # Show ETA once we have frame_total
                        )

                    # Record last update time
                    last_time_update = current_time

                if not ready:
                    if self.canceling and not current_frame_in_progress:
                        break
                    elif self.canceling and not graceful_shutdown_requested:
                        try:
                            os.kill(self.process.pid, signal.SIGUSR1)
                            graceful_shutdown_requested = True
                        except (AttributeError, ProcessLookupError):
                            pass
                    continue

                line = self.process.stdout.readline()
                if not line:
                    break

                line = line.decode(errors='backslashreplace').rstrip()
                line = line.replace('[Redshift] ', '').replace('[Redshift]', '')

                # Emit raw output signal
                if self.raw_output_callback:
                    self.raw_output_callback(line)

                # Check for saved file messages
                saved_file_match = re.search(r"Saved file ['\"]([^'\"]+\.(?:exr|png|jpg|jpeg|tif|tiff))['\"]", line)
                if saved_file_match:
                    output_file = saved_file_match.group(1)
                    # Emit image update signal
                    if self.image_update_callback:
                        self.image_update_callback(output_file)

                # Try different patterns to detect frame range information
                frame_range_match = None

                # Pattern 1: Standard "Frame range: X-Y" format
                pattern1 = re.search(r"Frame range: (\d+)-(\d+)", line)
                if pattern1:
                    frame_range_match = pattern1

                # Pattern 2: Try to match the actual start and end frame from the command
                if not frame_range_match and "hip file" in line.lower():
                    pattern2 = re.search(r"-s (\d+) -e (\d+)", line)
                    if pattern2:
                        frame_range_match = pattern2

                # Pattern 3: Look for ROP output with frame range info
                if not frame_range_match:
                    pattern3 = re.search(r"ROP.*f1:(\d+).*f2:(\d+)", line)
                    if pattern3:
                        frame_range_match = pattern3

                if frame_range_match and not frame_total_from_args:
                    start_frame = int(frame_range_match.group(1))
                    end_frame = int(frame_range_match.group(2))
                    frame_total = end_frame - start_frame + 1

                    # Update progress with frame range
                    if self.progress_callback:
                        self.progress_callback(frame_count, frame_total)

                    # Now that we have frame_total, do an initial estimate
                    if self.time_labels_callback:
                        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
                        # Initial guess: 5 seconds per frame if we have no data yet
                        est_total_time = 5.0 * frame_total
                        remaining_time = est_total_time - elapsed_time
                        eta_time = datetime.datetime.now() + datetime.timedelta(seconds=remaining_time)
                        last_eta_time = eta_time  # Store this initial ETA

                        self.time_labels_callback(
                            elapsed_time,   # Current elapsed time
                            0.0,            # No average yet
                            est_total_time, # Initial guess for total time
                            remaining_time, # Initial guess for remaining time
                            eta_time,       # Initial ETA
                            True            # Show ETA now that we have a frame range
                        )

                # Fallback: If we still have no frame_total but have command line arguments
                if frame_total == 0 and "-s" in line and "-e" in line and not frame_total_from_args:
                    frame_arg_match = re.search(r"-s (\d+).*-e (\d+)", line)
                    if frame_arg_match:
                        start_frame = int(frame_arg_match.group(1))
                        end_frame = int(frame_arg_match.group(2))
                        step = 1

                        # Try to find step size
                        step_match = re.search(r"-t (\d+)", line)
                        if step_match:
                            step = int(step_match.group(1))

                        # Calculate total frames with step
                        frame_total = len(range(start_frame, end_frame + 1, step))

                        # Update progress with frame range
                        if self.progress_callback:
                            self.progress_callback(frame_count, frame_total)

                        # Once we've set frame_total from arguments, don't overwrite it later
                        frame_total_from_args = True

                # Track when a frame is about to be rendered
                frame_rendering_match = re.search(r"'([^']+)' rendering frame (\d+)", line)
                if frame_rendering_match:
                    current_frame_number = int(frame_rendering_match.group(2))
                    # Store the start time for this frame
                    frame_start_times[current_frame_number] = datetime.datetime.now()
                    current_frame_start_time = datetime.datetime.now()  # For tracking current frame

                    # Fallback: If we still haven't detected a frame range but have seen a frame number,
                    # at least update the total frames to something greater than the current frame
                    if frame_total <= current_frame_number and not frame_total_from_args:
                        # Set frame_total to at least current frame number + estimated total
                        new_total = max(current_frame_number + 5, frame_total)
                        if new_total != frame_total:
                            frame_total = new_total
                            if self.progress_callback:
                                self.progress_callback(frame_count, frame_total)

                # Check if the frame is being skipped
                if 'Skip rendering enabled. File already rendered' in line or 'Skipped - File already exists' in line:
                    if current_frame_number is not None:
                        # Process frame as skipped
                        skipped_frames.add(current_frame_number)
                        frames_seen.add(current_frame_number)
                        frame_count = len(frames_seen)

                        # Emit frame skipped signal
                        if self.frame_skipped_callback:
                            self.frame_skipped_callback(current_frame_number)

                        consecutive_skips.append(current_frame_number)

                        # Update UI with skipped frame
                        if self.progress_callback:
                            self.progress_callback(frame_count, frame_total)

                        # Calculate elapsed time
                        current_time = datetime.datetime.now()
                        elapsed_time = (current_time - start_time).total_seconds()

                        # Update time labels when frames are skipped
                        if self.time_labels_callback and frame_total > 0:
                            # Use current average if available or default to elapsed / frames done
                            if average > 0:
                                avg_time = average
                            elif frame_count > 0:
                                avg_time = elapsed_time / frame_count  # Use current pace
                            else:
                                avg_time = max(1.0, elapsed_time)  # Some reasonable minimum

                            # Calculate remaining time and total estimates
                            remaining_frames = max(0, frame_total - frame_count)
                            remaining = remaining_frames * avg_time
                            est_total = elapsed_time + remaining  # Live elapsed + projected remaining

                            # Calculate ETA
                            eta_time = current_time + datetime.timedelta(seconds=remaining) if remaining > 0 else current_time
                            last_eta_time = eta_time  # Store this valid ETA

                            self.time_labels_callback(
                                elapsed_time,  # Elapsed time so far (live value)
                                avg_time,      # Average per frame (best estimate)
                                est_total,     # Elapsed + Remaining time
                                remaining,     # Remaining time
                                eta_time,      # ETA time
                                True           # Always show ETA once we have frame count
                            )

                            # Update last update time
                            last_time_update = current_time

                        last_message_type = "skipped"
                        # Mark that we're not rendering this frame
                        current_frame_in_progress = False
                        # Clear current frame number to prevent output
                        current_frame_number = None

                # For non-skipped frames, detect when they start rendering
                elif 'Loading RS rendering options' in line and current_frame_number is not None:
                    # Only process if we haven't seen this frame in skipped_frames
                    if current_frame_number not in skipped_frames:
                        current_frame_in_progress = True

                        # Count this frame as seen
                        frames_seen.add(current_frame_number)

                        # Get time estimates
                        estimated_time = 0
                        if frame_times:
                            if len(frame_times) >= 2:
                                estimated_time = recent_average
                            else:
                                estimated_time = average

                        # Output frame header
                        if not consecutive_skips and self.output_callback:
                            start_time_frame = frame_start_times[current_frame_number]
                            # Color the frame header in green to indicate it's an active frame
                            frame_header = f"\n Frame {current_frame_number}\n"
                            self.output_callback(frame_header, color='#50c878', bold=True)

                            # Output the start time normally
                            frame_info = f"   {'Started':<8} {start_time_frame.strftime('%I:%M:%S %p')}\n"
                            if estimated_time > 0:
                                est_finish_time = start_time_frame + datetime.timedelta(seconds=estimated_time)
                                frame_info += f"   {'Estimate':<8} {est_finish_time.strftime('%I:%M:%S %p')} - {self._format_time(estimated_time)}\n"
                            self.output_callback(frame_info)

                        # Update frame count based on seen frames
                        frame_count = len(frames_seen)

                        # Update progress
                        if self.progress_callback:
                            self.progress_callback(frame_count, frame_total)

                        current_frame_start = datetime.datetime.now()

                # Check for ROP node endRender (frame completion)
                elif 'ROP node endRender' in line:
                    current_frame_in_progress = False
                    if self.canceling and graceful_shutdown_requested:
                        if self.render_finished_callback:
                            self.render_finished_callback()
                        break

                # Check for Redshift block progress
                block_match = re.search(r'Block (\d+)/(\d+)', line)
                if block_match and current_frame_number is not None:
                    block_num = int(block_match.group(1))
                    total_blocks = int(block_match.group(2))
                    completed_blocks.add(block_num)
                    percent = int((len(completed_blocks) / total_blocks) * 100)

                    # Emit frame progress signal
                    if self.frame_progress_callback:
                        self.frame_progress_callback(current_frame_number, percent)

                    # Even for partial frame progress, update time estimates
                    if frame_total > 0 and current_frame_start_time and self.time_labels_callback:
                        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()

                        if average > 0:
                            # Use known average for remaining frames
                            remaining_frames = max(0, frame_total - frame_count + 1)  # +1 for current frame
                            remaining_time = remaining_frames * average
                        elif frame_count > 1:
                            # Use current pace to estimate
                            current_pace = elapsed_time / (frame_count - 1 + (percent / 100))
                            remaining_frames = max(0, frame_total - frame_count + 1)  # +1 for current
                            remaining_time = remaining_frames * current_pace
                        else:
                            # Very rough estimate based on current progress of first frame
                            if percent > 0:
                                time_per_percent = (datetime.datetime.now() - current_frame_start_time).total_seconds() / percent
                                current_frame_remaining = time_per_percent * (100 - percent)
                                remaining_time = current_frame_remaining + (frame_total - 1) * (time_per_percent * 100)
                            else:
                                # Fallback if we have no progress yet
                                remaining_time = frame_total * 5.0  # Assume 5 seconds per frame

                        est_total_time = elapsed_time + remaining_time
                        eta_time = datetime.datetime.now() + datetime.timedelta(seconds=remaining_time)
                        last_eta_time = eta_time  # Store this valid ETA

                        self.time_labels_callback(
                            elapsed_time,    # Current elapsed time
                            average,         # Current average (might be 0 early on)
                            est_total_time,  # Estimated total
                            remaining_time,  # Remaining time
                            eta_time,        # ETA
                            True             # Show ETA
                        )

                # Check for frame completion (scene extraction time indicates completion)
                elif 'scene extraction time' in line:
                    if current_frame_start and current_frame_number is not None:
                        # Extract render time
                        match = re.search(r"total time (\d+\.\d+) sec", line)
                        if match:
                            render_time = float(match.group(1))
                            frame_times.append(render_time)

                            # Make sure this frame is counted
                            frames_seen.add(current_frame_number)
                            frame_count = len(frames_seen)

                            # Update progress with this completed frame
                            if self.progress_callback:
                                self.progress_callback(frame_count, frame_total)

                            # Emit frame completed signal
                            if self.frame_completed_callback:
                                self.frame_completed_callback(current_frame_number, render_time)

                            # Calculate averages
                            average = sum(frame_times) / len(frame_times)
                            if len(frame_times) >= 2:
                                recent_times = frame_times[-2:]
                                recent_average = max(0, (2 * recent_times[1]) - recent_times[0])
                            else:
                                recent_average = average

                            # Calculate elapsed time
                            current_time = datetime.datetime.now()
                            elapsed_time = (current_time - start_time).total_seconds()

                            # Calculate remaining time based on average
                            remaining_frames = max(0, frame_total - frame_count)
                            remaining_time = remaining_frames * average

                            # Calculate ETA
                            eta_time = current_time + datetime.timedelta(seconds=remaining_time)
                            last_eta_time = eta_time  # Store this valid ETA

                            # Calculate estimated total time - always elapsed + remaining
                            est_total_time = elapsed_time + remaining_time

                            # Emit time labels signal
                            if self.time_labels_callback:
                                self.time_labels_callback(
                                    elapsed_time,      # Live elapsed time
                                    average,           # Average per frame
                                    est_total_time,    # Elapsed + remaining time
                                    remaining_time,    # Remaining time
                                    eta_time,          # ETA time
                                    True               # Show ETA
                                )

                                # Update last update time
                                last_time_update = current_time

                            # Output actual render time for this frame
                            if not consecutive_skips and self.output_callback:
                                finished_str = f"   {'Finished':<8} {current_time.strftime('%I:%M:%S %p')} - {self._format_time(render_time)}\n\n"
                                self.output_callback(finished_str)

                            last_message_type = "completed"

                            # Clear block tracking at end of frame
                            completed_blocks = set()
                            total_blocks = None

                # Check for special hardeen messages
                if line.startswith('hardeen_outputfile:'):
                    output_file = line.split(':', 1)[1].strip()
                    if self.image_update_callback:
                        self.image_update_callback(output_file)

            # Output any remaining skipped frames at the end
            if consecutive_skips and self.output_callback:
                consecutive_skips.sort()
                ranges = []
                start = end = consecutive_skips[0]

                for i in range(1, len(consecutive_skips)):
                    if consecutive_skips[i] == end + 1:
                        end = consecutive_skips[i]
                    else:
                        if start == end:
                            ranges.append(f"{start}")
                        else:
                            ranges.append(f"{start}-{end}")
                        start = end = consecutive_skips[i]

                if start == end:
                    ranges.append(f"{start}")
                else:
                    ranges.append(f"{start}-{end}")

                frames_text = ", ".join(ranges)
                self.output_callback(f"Frames {frames_text} skipped - Files already exist\n\n")

            # Make a final time update with the final stats
            if self.time_labels_callback:
                current_time = datetime.datetime.now()
                elapsed_time = (current_time - start_time).total_seconds()

                # Calculate final average if we have frames
                avg_time = sum(frame_times) / len(frame_times) if frame_times else 0

                # For the final update, preserve the final statistics
                # Display actual elapsed time as both elapsed and total time
                # since the render is complete (no remaining time)
                self.time_labels_callback(
                    elapsed_time,  # Final elapsed time
                    avg_time,      # Final average per frame
                    elapsed_time,  # Final total time (same as elapsed since we're done)
                    0.0,           # No remaining time
                    current_time,  # Current time as ETA
                    False          # Don't show ETA anymore
                )

            # Signal render finished when done
            if self.render_finished_callback:
                self.render_finished_callback()

        except Exception as e:
            import traceback
            print(f"Error in monitor thread: {str(e)}\n{traceback.format_exc()}")
            if self.render_finished_callback:
                self.render_finished_callback()

    def is_rendering(self) -> bool:
        """Check if rendering is in progress"""
        return self.process is not None and self.process.poll() is None

    def _format_time(self, seconds: float) -> str:
        """Format seconds into human readable time"""
        timedelta = datetime.timedelta(seconds=seconds)
        days = timedelta.days
        hours, remainder = divmod(timedelta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds or not any((days, hours, minutes)):
            parts.append(f"{seconds}s")
        return "".join(parts)
