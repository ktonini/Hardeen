import OpenImageIO as oiio
import numpy as np
from PIL import Image
from PySide6.QtGui import QPixmap, QImage
import os
import traceback
import time

def load_exr_aovs(image_path, max_aovs=20, max_retries=3):
    """
    Load an EXR file, extract all AOVs/subimages, and return a list of (QPixmap, label) tuples.

    Args:
        image_path: Path to the EXR file
        max_aovs: Maximum number of AOVs to extract
        max_retries: Maximum number of retries for loading the file

    Returns:
        List of (QPixmap, label) tuples for each AOV
    """
    images = []

    # Safety check for file existence
    if not os.path.exists(image_path):
        print(f"EXR ERROR: File does not exist: {image_path}")
        return images

    # Implement a retry mechanism with exponential backoff
    retry_count = 0
    last_error = None
    last_file_size = 0

    while retry_count < max_retries:
        try:
            # Check if file size is stable
            try:
                current_size = os.path.getsize(image_path)
                if current_size == last_file_size:
                    # File size is stable, proceed with loading
                    pass
                else:
                    # File size changed, update and wait before retry
                    last_file_size = current_size
                    wait_time = 0.5 * (2 ** retry_count)  # Exponential backoff
                    print(f"EXR file size changed to {current_size} bytes, waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
            except Exception as e:
                # Ignore errors in file size check
                pass

            # First check if we can open the file with ImageInput
            inp = oiio.ImageInput.open(image_path)
            if not inp:
                # Use geterror() to get the specific error message
                err = oiio.geterror() if hasattr(oiio, 'geterror') else "Unknown error"
                last_error = f"Cannot open file: {image_path} - {err}"

                # Check if this is an "unexpected end of file" error, which suggests
                # the file is still being written
                if "unexpected end of file" in err.lower():
                    # Wait with exponential backoff before retry
                    wait_time = 0.5 * (2 ** retry_count)  # Exponential backoff
                    print(f"EXR file appears to be partially written, waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
                else:
                    # Other error, print and return
                    print(f"EXR ERROR: {last_error}")
                    return images

            # Get file info
            spec = inp.spec()

            # Close the input
            inp.close()

            # Now try to use ImageBuf and work with subimages
            try:
                # Get the number of subimages by opening the first one
                buf = oiio.ImageBuf(image_path)
                # Check for error using geterror() instead of has_error()
                error_msg = buf.geterror()
                if error_msg:
                    last_error = f"Failed to create ImageBuf: {error_msg}"
                    # Check if this is an "unexpected end of file" error
                    if "unexpected end of file" in error_msg.lower():
                        # Wait with exponential backoff before retry
                        wait_time = 0.5 * (2 ** retry_count)
                        print(f"EXR buffer creation failed, waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    else:
                        # Other error, print and return
                        print(f"EXR ERROR: {last_error}")
                        return images

                num_subimages = buf.nsubimages

                if num_subimages == 0:
                    print(f"EXR ERROR: No subimages found in file: {image_path}")
                    return images
            except Exception as e:
                last_error = f"Failed to create ImageBuf: {str(e)}"
                print(f"EXR ERROR: {last_error}")
                traceback.print_exc()
                # Don't retry on exceptions other than "unexpected end of file"
                if "unexpected end of file" in str(e).lower():
                    wait_time = 0.5 * (2 ** retry_count)
                    print(f"EXR exception during buffer creation, waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
                return images

            # Process each subimage/AOV
            for subCount in range(min(num_subimages, max_aovs)):
                try:
                    # Load subimage
                    subimage = oiio.ImageBuf(image_path, subCount, 0)
                    # Check for error
                    error_msg = subimage.geterror()
                    if error_msg:
                        print(f"EXR ERROR: Failed to load subimage {subCount}: {error_msg}")
                        continue

                    # Get channel names for this subimage
                    spec = subimage.spec()
                    channelnames = spec.channelnames

                    # Skip subimages with no channels
                    if not channelnames:
                        continue

                    # Extract layer information
                    layers = {}
                    for channelname in channelnames:
                        layername = ".".join(channelname.split(".")[:-1])
                        if layername not in layers:
                            layers[layername] = []
                        layers[layername].append(channelname)

                    # Create label text
                    layer_str = None
                    for layername, channelnames in layers.items():
                        channels = [cn.split(".")[-1].lower() for cn in channelnames]
                        if len(channels) == 1:
                            channel_str = channels[0]
                        else:
                            channel_str = "".join(channels)
                        if layername == "":
                            layer_str = f"{channel_str}"
                        else:
                            layer_str = f"{layername}.{channel_str}"

                    # If we couldn't determine a layer name, use a default
                    if not layer_str:
                        layer_str = f"Layer {subCount}"

                    try:
                        # Convert to display format
                        display_buf = oiio.ImageBufAlgo.colorconvert(subimage, "linear", "srgb")
                        error_msg = display_buf.geterror()
                        if error_msg:
                            print(f"EXR ERROR: Failed to convert color space for subimage {subCount}: {error_msg}")
                            continue

                        # Get pixels with error handling
                        pixels = display_buf.get_pixels(oiio.FLOAT)
                        if pixels is None or pixels.size == 0:
                            print(f"EXR ERROR: Failed to get pixels for subimage {subCount}")
                            continue

                        # Handle different channel configurations
                        if len(pixels.shape) == 3:
                            if pixels.shape[2] == 1:  # Single channel
                                pixels = np.repeat(pixels, 3, axis=2)
                            elif pixels.shape[2] not in [3, 4]:  # Not RGB or RGBA
                                if pixels.shape[2] > 3:
                                    pixels = pixels[:, :, :3]
                                else:
                                    padding = np.zeros((*pixels.shape[:2], 3-pixels.shape[2]))
                                    pixels = np.concatenate([pixels, padding], axis=2)
                        elif len(pixels.shape) == 2:  # Single channel
                            pixels = np.stack([pixels] * 3, axis=2)

                        # Normalize the float data to 0-1 range
                        pixels = np.clip(pixels, 0, 1)

                        # Convert to 8-bit
                        pixels = (pixels * 255).astype(np.uint8)

                        # Convert to QPixmap through PIL Image
                        img = Image.fromarray(pixels)
                        img_bytes = img.tobytes("raw", "RGB")
                        qimg = QImage(img_bytes, img.width, img.height, QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimg)

                        # Add to result list
                        images.append((pixmap, layer_str))

                    except Exception as e:
                        print(f"EXR ERROR: Failed to process subimage {subCount}: {str(e)}")

                except Exception as e:
                    print(f"EXR ERROR: Failed to access subimage {subCount}: {str(e)}")

            # Only print a summary at the end if successful
            if images:
                # Skip printing even the success message to keep the terminal clean
                pass

            # If we got here successfully, break out of the retry loop
            break

        except Exception as e:
            last_error = str(e)
            print(f"EXR ERROR: Failed to load file: {str(e)}")
            traceback.print_exc()

            # Check if this is an "unexpected end of file" error
            if "unexpected end of file" in str(e).lower():
                wait_time = 0.5 * (2 ** retry_count)
                print(f"EXR general exception, waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
                retry_count += 1
                continue
            return images

        # Increment retry count
        retry_count += 1

    # If we've exhausted all retries and still have no images
    if not images and last_error and retry_count >= max_retries:
        print(f"EXR ERROR: Failed to load file after {max_retries} retries: {last_error}")

    return images
