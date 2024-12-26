import logging
import os
from pathlib import Path
from main import ImageOptimizer

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def test_optimizer(image_path: str):

    # Initialize optimizer
    optimizer = ImageOptimizer()

    # Test cases with larger sizes for high-res images
    test_sizes = [10, 15, 20]  # Target sizes in KB

    # Verify file exists
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return

    try:
        with open(image_path, 'rb') as f:
            test_image = f.read()

        print(f"\nProcessing image: {image_path}")
        print(f"Original file size: {len(test_image) / 1024:.2f}KB")

        # Create output directory if it doesn't exist
        output_dir = Path('optimized_images')
        output_dir.mkdir(exist_ok=True)

        # Test different target sizes
        for target_size in test_sizes:
            print(f"\nTesting target size: {target_size}KB")
            result = optimizer.optimize_image(test_image, target_size)

            if result:
                optimized_data, metadata = result
                print("\nOptimization successful!")
                print(f"Original size: {metadata['original_size_kb']:.2f}KB")
                print(f"Final size: {metadata['final_size_kb']:.2f}KB")
                print(f"Quality: {metadata['quality']}")
                print(f"Dimensions: {metadata['dimensions']}")
                print(f"Original format: {metadata.get('original_format', 'unknown')}")

                # Save optimized image
                output_filename = output_dir / f'optimized_{target_size}kb.jpg'
                with open(output_filename, 'wb') as f:
                    f.write(optimized_data)
                print(f"Saved optimized image as: {output_filename}")
            else:
                print("Optimization failed!")

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    setup_logging()

    # You can specify your image path here
    image_path = "face.jpg"  # Update this to your image path
    test_optimizer(image_path)