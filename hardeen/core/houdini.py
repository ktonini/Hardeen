import os
import json
import subprocess
from pathlib import Path
from typing import Tuple, List, Dict, Optional

class HoudiniManager:
    """Manages Houdini-specific operations and interactions"""

    @staticmethod
    def get_houdini_history_file() -> Optional[str]:
        """Get the path to the Houdini file.history"""
        home = str(Path.home())

        # Look for any houdini version directory
        houdini_dirs = [d for d in os.listdir(home)
                       if d.startswith('houdini') and
                       os.path.isdir(os.path.join(home, d)) and
                       not d.endswith('.py')]

        if not houdini_dirs:
            return None

        # Use the latest version if multiple exist
        latest_dir = sorted(houdini_dirs)[-1]
        history_file = os.path.join(home, latest_dir, 'file.history')

        return history_file if os.path.exists(history_file) else None

    @staticmethod
    def parse_hip_files(history_file: str) -> List[str]:
        """Parse the file.history and extract HIP files"""
        if not history_file:
            return []

        try:
            with open(history_file, 'r') as f:
                content = ''.join(f.read().splitlines())

            if not content.startswith('HIP{'):
                return []

            end = content.find('}', 4)
            if end == -1:
                return []

            hip_section = content[4:end]
            paths = []
            current_path = ""

            for part in hip_section.split('/'):
                if not part:
                    continue

                if not current_path:
                    current_path = '/' + part
                else:
                    current_path += '/' + part

                if current_path.endswith('.hip'):
                    paths.append(current_path)
                    current_path = ""

            # Remove duplicates while preserving order
            seen = set()
            hip_files = []
            for path in paths:
                if path not in seen:
                    seen.add(path)
                    hip_files.append(path)

            # Reverse the list so newest files appear first
            hip_files.reverse()
            return hip_files

        except Exception as e:
            print(f"Error reading history file: {e}")
            return []

    @staticmethod
    def parse_out_nodes(hip_file: str) -> Tuple[List[str], Dict[str, dict]]:
        """Parse the hip file and extract available ROP nodes and their settings"""
        try:
            import hou
            return HoudiniManager._parse_out_nodes_hou(hip_file)
        except ImportError:
            return HoudiniManager._parse_out_nodes_hython(hip_file)

    @staticmethod
    def _parse_out_nodes_hou(hip_file: str) -> Tuple[List[str], Dict[str, dict]]:
        """Parse out nodes using Houdini Python API"""
        import hou
        hou.hipFile.load(hip_file)

        out_nodes = []
        node_settings = {}
        out_context = hou.node("/out")

        if out_context:
            for node in out_context.children():
                if node.type().name() in ["rop_geometry", "Redshift_ROP", "opengl"]:
                    node_path = node.path()
                    out_nodes.append(node_path)

                    settings = {
                        'f1': int(node.parm('f1').eval()) if node.parm('f1') else 1,
                        'f2': int(node.parm('f2').eval()) if node.parm('f2') else 1,
                        'skip_rendered': node.parm('RS_outputSkipRendered').eval() if node.parm('RS_outputSkipRendered') else 0
                    }
                    node_settings[node_path] = settings

        return out_nodes, node_settings

    @staticmethod
    def _parse_out_nodes_hython(hip_file: str) -> Tuple[List[str], Dict[str, dict]]:
        """Parse out nodes using hython as fallback"""
        script = """
import hou
import sys
import os
import json

# Completely suppress stdout/stderr
class NullIO:
    def write(self, *args): pass
    def flush(self): pass

# Save original stdout/stderr
old_stdout = sys.stdout
old_stderr = sys.stderr

try:
    # Redirect all output to null
    sys.stdout = NullIO()
    sys.stderr = NullIO()

    # Set environment variables to suppress Redshift output
    os.environ['RS_VERBOSITY_LEVEL'] = '0'

    # Load the hip file silently
    hou.hipFile.load(r"{0}", suppress_save_prompt=True)

    # Restore stdout just to print node paths and settings
    sys.stdout = old_stdout

    # Get out nodes and their settings
    out_context = hou.node("/out")
    node_settings = {{}}

    if out_context:
        for node in out_context.children():
            if node.type().name() in ["rop_geometry", "Redshift_ROP", "opengl"]:
                node_path = node.path()
                print("NODE:{{}}".format(node_path))

                # Get frame range and skip settings
                settings = {{
                    'f1': int(node.parm('f1').eval()) if node.parm('f1') else 1,
                    'f2': int(node.parm('f2').eval()) if node.parm('f2') else 1,
                    'skip_rendered': node.parm('RS_outputSkipRendered').eval() if node.parm('RS_outputSkipRendered') else 0
                }}
                print("SETTINGS:{{}}".format(json.dumps(settings)))

finally:
    # Restore original stdout/stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr
""".format(hip_file)

        try:
            env = os.environ.copy()
            env['HOU_VERBOSITY'] = '0'
            env['RS_VERBOSITY_LEVEL'] = '0'

            result = subprocess.run(
                ['hython', '-c', script],
                capture_output=True,
                text=True,
                env=env,
                encoding='utf-8'
            )

            nodes = []
            node_settings = {}

            current_node = None
            for line in result.stdout.splitlines():
                if line.startswith('NODE:'):
                    current_node = line[5:].strip()
                    nodes.append(current_node)
                elif line.startswith('SETTINGS:'):
                    if current_node:
                        settings = json.loads(line[9:])
                        node_settings[current_node] = settings

            return nodes, node_settings

        except Exception as e:
            print(f"Error running hython: {e}")
            return [], {}
