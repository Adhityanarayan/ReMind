Tips & next steps

- To run on a remote machine without a GUI, use `detect_image.py` only.
- For better accuracy, consider using DNN-based detectors (OpenCV DNN, MTCNN, or pretrained models) instead of Haar cascades.
- If you want a packaged CLI, consider adding `argparse` options to `detect_camera.py` for camera index, output video recording, and scaling options.
