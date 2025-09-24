#!/usr/bin/env python3
"""CSV analysis script - delegates to unified FMF CLI."""

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
        new_args = ["fmf", "csv", "analyse"]
        
        # Process arguments
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg == "--input":
                new_args.extend(["--input", args[i + 1]])
                i += 2
            elif arg == "--text-col":
                new_args.extend(["--text-col", args[i + 1]])
                i += 2
            elif arg == "--id-col":
                new_args.extend(["--id-col", args[i + 1]])
                i += 2
            elif arg == "--prompt":
                new_args.extend(["--prompt", args[i + 1]])
                i += 2
            elif arg in ["-c", "--config"]:
                new_args.extend(["-c", args[i + 1]])
                i += 2
            elif arg == "--output-csv":
                new_args.extend(["--output-csv", args[i + 1]])
                i += 2
            elif arg == "--output-jsonl":
                new_args.extend(["--output-jsonl", args[i + 1]])
                i += 2
            elif arg == "--output-format":
                new_args.extend(["--response", args[i + 1]])
                i += 2
            elif arg == "--enable-rag":
                new_args.append("--rag")
                i += 1
            elif arg == "--rag-pipeline":
                new_args.extend(["--rag-pipeline", args[i + 1]])
                i += 2
            elif arg == "--service":
                new_args.extend(["--service", args[i + 1]])
                i += 2
            elif arg == "--mode":
                new_args.extend(["--mode", args[i + 1]])
                i += 2
            elif arg == "--expects-json":
                new_args.append("--expects-json")
                i += 1
            elif arg == "--no-expects-json":
                new_args.append("--no-expects-json")
                i += 1
            elif arg == "--json":
                # JSON output is handled differently in the new CLI
                i += 1
            elif arg in ["-h", "--help"]:
                # Show help for the new CLI
                try:
                    subprocess.run(["fmf", "csv", "analyse", "--help"], check=True)
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