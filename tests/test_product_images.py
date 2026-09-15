"""Image regression checks without importing app or connecting to production DB."""
import ast
import io
from pathlib import Path
import unittest
from PIL import Image

source = ast.parse((Path(__file__).resolve().parents[1] / 'app.py').read_text())
names = {'_prepare_product_image', '_encode_product_image', '_encode_product_upload'}
namespace = {'io': io}
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), 'image_helpers', 'exec'), namespace)

class ProductImages(unittest.TestCase):
    def test_palette_edges_are_smooth_and_transparent(self):
        original = Image.new('P', (2400, 1600))
        original.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
        original.info['transparency'] = 0
        original.paste(1, (601, 401, 1801, 1201))
        image = namespace['_prepare_product_image'](original)
        image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        buf, ext = namespace['_encode_product_image'](image)
        saved = Image.open(buf)
        self.assertEqual((ext, saved.size), ('png', (1200, 800)))
        self.assertEqual(saved.getpixel((0, 0))[3], 0)
        self.assertEqual(saved.getpixel((600, 400)), (255, 0, 0, 255))
        self.assertTrue(any(0 < a < 255 for a in saved.getchannel('A').getdata()))

    def test_camera_orientation(self):
        image = Image.new('RGBA', (40, 80), (20, 30, 40, 100))
        image.getexif()[274] = 6
        saved = namespace['_prepare_product_image'](image)
        self.assertEqual(saved.size, (80, 40))
        self.assertEqual(saved.getpixel((0, 0)), (20, 30, 40, 100))

    def test_opaque_photos_stay_compressed(self):
        _, ext = namespace['_encode_product_image'](namespace['_prepare_product_image'](Image.new('RGB', (30, 60))))
        self.assertEqual(ext, 'jpg')

    def test_upload_is_bounded_and_preserves_alpha(self):
        image = Image.new('RGBA', (2400, 1600), (30, 60, 90, 0))
        image.paste((200, 70, 30, 128), (300, 300, 1800, 1200))
        out, ext = namespace['_encode_product_upload'](image)
        saved = Image.open(out)
        self.assertEqual(saved.size, (1200, 800))
        self.assertEqual(saved.convert('RGBA').getpixel((0, 0))[3], 0)
        self.assertEqual(saved.convert('RGBA').getpixel((500, 400))[3], 128)
        base, _ = namespace['_encode_product_image'](image)
        self.assertLessEqual(len(out.getvalue()), len(base.getvalue()))

    def test_upload_does_not_upscale(self):
        out, _ = namespace['_encode_product_upload'](Image.new('RGB', (80, 160)))
        self.assertEqual(Image.open(out).size, (80, 160))

if __name__ == '__main__':
    unittest.main()
