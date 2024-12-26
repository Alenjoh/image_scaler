from PIL import Image, ExifTags
import io
from typing import Tuple, Optional
import logging
import math


class ImageOptimizer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.SUPPORTED_FORMATS = {'PNG', 'JPEG', 'JPG', 'WEBP', 'MPO', 'HEIC', 'BMP', 'TIFF'}
        self.MIN_DIMENSION = 300

    def _get_optimal_dimensions(
            self,
            width: int,
            height: int,
            target_size_kb: int,
            current_size_kb: float
    ) -> Tuple[int, int]:
        """Calculate optimal dimensions while maintaining aspect ratio"""
        # If the target size is larger than current size, keep original dimensions
        if target_size_kb >= current_size_kb:
            return width, height

        # Calculate aspect ratio
        aspect_ratio = width / height

        # Calculate scaling factor based on target vs current size
        # Using square root as image size typically scales with area
        scale_factor = math.sqrt(target_size_kb / current_size_kb)

        # Initial new dimensions
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        # Ensure minimum dimension is maintained
        if new_width < self.MIN_DIMENSION:
            new_width = self.MIN_DIMENSION
            new_height = int(new_width / aspect_ratio)
        elif new_height < self.MIN_DIMENSION:
            new_height = self.MIN_DIMENSION
            new_width = int(new_height * aspect_ratio)

        # Ensure dimensions are even numbers (some image formats prefer this)
        new_width = (new_width // 2) * 2
        new_height = (new_height // 2) * 2

        return new_width, new_height

    def _fix_orientation(self, img: Image.Image) -> Image.Image:
        """Fix image orientation based on EXIF data"""
        try:
            # Get EXIF data
            if hasattr(img, '_getexif'):  # Check if image has EXIF
                exif = img._getexif()
                if exif is None:
                    return img

                # Find orientation tag
                orientation_key = None
                for key in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[key] == 'Orientation':
                        orientation_key = key
                        break

                if orientation_key is None or orientation_key not in exif:
                    return img

                orientation = exif[orientation_key]

                # Rotate or flip based on orientation value
                rotation_table = {
                    1: lambda x: x,  # Normal
                    2: lambda x: x.transpose(Image.FLIP_LEFT_RIGHT),  # Mirrored
                    3: lambda x: x.rotate(180, expand=True),  # 180
                    4: lambda x: x.transpose(Image.FLIP_TOP_BOTTOM),  # Flipped
                    5: lambda x: x.transpose(Image.FLIP_LEFT_RIGHT).rotate(90, expand=True),
                    6: lambda x: x.rotate(-90, expand=True),  # 90 CW
                    7: lambda x: x.transpose(Image.FLIP_LEFT_RIGHT).rotate(-90, expand=True),
                    8: lambda x: x.rotate(90, expand=True),  # 90 CCW
                }

                if orientation in rotation_table:
                    img = rotation_table[orientation](img)
                    self.logger.info(f"Applied orientation correction: {orientation}")

        except Exception as e:
            self.logger.warning(f"Error fixing orientation: {str(e)}")

        return img

    def _compress_image(
            self,
            img: Image.Image,
            target_size_kb: int,
            max_quality: int = 95,
            min_quality: int = 40,
            quality_steps: int = 5
    ) -> Tuple[bytes, int]:
        """Compress image using binary search for optimal quality"""
        quality = max_quality
        best_quality = max_quality
        best_data = None
        best_size = float('inf')

        while quality >= min_quality:
            try:
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                data = buffer.getvalue()
                size_kb = len(data) / 1024

                self.logger.debug(f"Tried quality: {quality}, Size: {size_kb:.2f}KB")

                if abs(size_kb - target_size_kb) < abs(best_size - target_size_kb):
                    best_quality = quality
                    best_data = data
                    best_size = size_kb

                if size_kb > target_size_kb:
                    quality -= quality_steps
                else:
                    break

            except Exception as e:
                self.logger.error(f"Compression error at quality {quality}: {str(e)}")
                quality -= quality_steps

        return best_data, best_quality

    def optimize_image(
            self,
            input_data: bytes,
            target_size_kb: int,
            maintain_format: bool = False
    ) -> Optional[Tuple[bytes, dict]]:
        """Optimize image to target size while maintaining maximum quality"""
        try:
            # Load image
            img = Image.open(io.BytesIO(input_data))

            # Fix orientation first
            img = self._fix_orientation(img)

            original_format = img.format
            self.logger.info(f"Processing image of format: {original_format}")

            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P', 'CMYK'):
                img = img.convert('RGB')
                self.logger.info(f"Converted image from {img.mode} to RGB")

            # Get current size
            current_size_kb = len(input_data) / 1024
            self.logger.info(f"Original size: {current_size_kb:.2f}KB")

            # Calculate new dimensions
            original_width, original_height = img.size
            new_width, new_height = self._get_optimal_dimensions(
                original_width,
                original_height,
                target_size_kb,
                current_size_kb
            )

            # Resize if needed
            if (new_width, new_height) != (original_width, original_height):
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.logger.info(f"Resized to: {new_width}x{new_height}")

            # Compress to reach target size
            optimized_data, quality = self._compress_image(img, target_size_kb)

            if optimized_data is None:
                self.logger.error("Compression failed to produce valid output")
                return None

            final_size_kb = len(optimized_data) / 1024

            metadata = {
                'original_size_kb': current_size_kb,
                'final_size_kb': final_size_kb,
                'quality': quality,
                'resized': (new_width, new_height) != (original_width, original_height),
                'dimensions': f"{new_width}x{new_height}",
                'original_format': original_format
            }

            self.logger.info(f"Final size: {final_size_kb:.2f}KB, Quality: {quality}")
            return optimized_data, metadata

        except Exception as e:
            self.logger.error(f"Optimization failed: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None