#!/usr/bin/env python3
"""Text to JSON script - delegates to unified FMF CLI."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Delegate to the unified FMF CLI."""
    
    # Get the script directory to find the fmf CLI
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Try to run the fmf CLI
    try:
        # Convert sys.argv to the new CLI format
        args = sys.argv[1:]  # Remove script name
        
        # Map old arguments to new CLI format
        new_args = ["fmf", "text"]
        
        # Process arguments
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg in ["-c", "--config"]:
                new_args.extend(["-c", args[i + 1]])
                i += 2
            elif arg == "--json":
                # JSON output is handled differently in the new CLI
                i += 1
            elif arg == "--enable-rag":
                new_args.append("--rag")
                i += 1
            elif arg == "--rag-pipeline":
                new_args.extend(["--rag-pipeline", args[i + 1]])
                i += 2
            elif arg == "--mode":
                new_args.extend(["--mode", args[i + 1]])
                i += 2
            elif arg in ["-h", "--help"]:
                # Show help for the new CLI
                try:
                    subprocess.run(["fmf", "text", "--help"], check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("FMF CLI not found. Please install the package properly.")
                    return 1
                return 0
            else:
                # Unknown argument - pass through
                new_args.append(arg)
                i += 1
        
        # Run the new CLI
        try:
            result = subprocess.run(new_args, cwd=project_root, check=True)
            return result.returncode
        except subprocess.CalledProcessError as e:
            return e.returncode
        except FileNotFoundError:
            print("Error: FMF CLI not found. Please ensure the package is installed correctly.", file=sys.stderr)
            return 1
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())