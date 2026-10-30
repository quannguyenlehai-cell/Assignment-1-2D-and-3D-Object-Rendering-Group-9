"""Run from any working directory: python path/to/cg_assignment1/main.py."""
import argparse
import sys
import glfw


def main():
    parser = argparse.ArgumentParser(description='HCMUT Computer Graphics Assignment 1')
    parser.add_argument('--frames', type=int, default=0, help='Exit after N frames (smoke check).')
    args = parser.parse_args()
    if not glfw.init():
        print('GLFW initialization failed. Run in a desktop session with an OpenGL 3.3 driver.', file=sys.stderr)
        return 1
    app = None
    try:
        from assignment.app import AssignmentApp
        app = AssignmentApp()
        app.run(args.frames)
        return 0
    finally:
        if app is not None:
            app.close()
        glfw.terminate()


if __name__ == '__main__':
    raise SystemExit(main())
