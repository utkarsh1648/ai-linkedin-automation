import os
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import config
from utils.logger import get_logger

logger = get_logger(__name__)

class VisualService:
    """
    Generates branded social media cards for AI news.
    """
    def __init__(self):
        self.width = 1080
        self.height = 1080
        self.bg_color = (15, 15, 15)  # Dark theme
        self.accent_color = (0, 87, 255)  # Brand Blue
        self.text_color = (255, 255, 255)
        self.secondary_text_color = (180, 180, 180)
        
        # Font paths - common Windows paths
        self.font_bold = self._find_font(["arialbd.ttf", "segoeuib.ttf", "Roboto-Bold.ttf"])
        self.font_regular = self._find_font(["arial.ttf", "segoeui.ttf", "Roboto-Regular.ttf"])

    def _find_font(self, font_names: list) -> str:
        """Attempts to find a system font from a list of possibilities."""
        search_paths = [
            "C:\\Windows\\Fonts\\",
            "/usr/share/fonts/truetype/",
            "assets/fonts/"
        ]
        for path in search_paths:
            for name in font_names:
                full_path = os.path.join(path, name)
                if os.path.exists(full_path):
                    return full_path
        return None # Fallback to default PIL font

    def _wrap_text(self, text: str, font, max_width: int) -> list:
        """Wraps text to fit within a specified width."""
        lines = []
        words = text.split()
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            # Get length of the test line
            w = font.getlength(test_line)
            if w <= max_width:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def generate_news_card(self, headline: str, brand_name: str = "AI News Daily") -> str:
        """
        Creates a square news card with a headline and branding.
        Uses random themes to ensure variety.
        """
        import random
        
        # Define premium themes
        THEMES = [
            {"bg": (10, 10, 15), "accent": (0, 100, 255), "glow": (0, 40, 120), "name": "Deep Blue"},
            {"bg": (15, 10, 20), "accent": (150, 50, 255), "glow": (60, 20, 100), "name": "Royal Purple"},
            {"bg": (10, 15, 12), "accent": (0, 200, 120), "glow": (0, 80, 50), "name": "Emerald Tech"},
            {"bg": (18, 12, 10), "accent": (255, 100, 0), "glow": (120, 40, 0), "name": "Solar Flare"},
            {"bg": (20, 20, 20), "accent": (200, 200, 200), "glow": (60, 60, 60), "name": "Midnight Gray"}
        ]
        
        theme = random.choice(THEMES)
        bg_color = theme["bg"]
        accent_color = theme["accent"]
        glow_color = theme["glow"]

        try:
            # Create base image
            img = Image.new('RGB', (self.width, self.height), color=bg_color)
            draw = ImageDraw.Draw(img)

            # --- Add Advanced Background Gradients ---
            # Main Glow
            glow = Image.new('RGB', (self.width, self.height), (0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.ellipse([self.width//3, -self.height//3, self.width*1.4, self.height//1.5], fill=glow_color)
            
            # Secondary subtle glow for depth
            glow_draw.ellipse([-self.width//4, self.height//1.5, self.width//2, self.height*1.2], fill=(20, 20, 25))
            
            glow = glow.filter(ImageFilter.GaussianBlur(radius=180))
            img = Image.blend(img, glow, 0.6)
            draw = ImageDraw.Draw(img)

            # --- Draw Header Tag ---
            margin = 90
            tag_text = "🔥 TRENDING AI NEWS"
            tag_font_size = 32
            tag_font = ImageFont.truetype(self.font_bold, tag_font_size) if self.font_bold else ImageFont.load_default()
            
            draw.text((margin, margin), tag_text, font=tag_font, fill=accent_color)

            # --- Draw Headline ---
            headline_font_size = 78
            headline_font = ImageFont.truetype(self.font_bold, headline_font_size) if self.font_bold else ImageFont.load_default()
            
            wrapped_lines = self._wrap_text(headline, headline_font, self.width - (margin * 2))
            
            # Calculate text block height
            line_spacing = 25
            total_height = len(wrapped_lines) * (headline_font_size + line_spacing)
            y_start = (self.height // 2) - (total_height // 2)
            
            for i, line in enumerate(wrapped_lines):
                y = y_start + i * (headline_font_size + line_spacing)
                # Subtle drop shadow for readability
                draw.text((margin + 2, y + 2), line, font=headline_font, fill=(0, 0, 0))
                draw.text((margin, y), line, font=headline_font, fill=self.text_color)

            # --- Draw Footer / Branding ---
            footer_font_size = 38
            footer_font = ImageFont.truetype(self.font_regular, footer_font_size) if self.font_regular else ImageFont.load_default()
            
            # Bottom brand name
            draw.text((margin, self.height - margin - 50), brand_name, font=footer_font, fill=self.secondary_text_color)
            
            # Draw a sleek accent line
            draw.rectangle([margin, self.height - margin - 75, margin + 120, self.height - margin - 68], fill=accent_color)

            # --- Save Image ---
            os.makedirs(config.MEDIA_DIR, exist_ok=True)
            filename = f"news_card_{uuid.uuid4().hex[:8]}.png"
            file_path = os.path.join(config.MEDIA_DIR, filename)
            img.save(file_path)
            
            logger.info(f"VisualService: News card generated using theme '{theme['name']}' at {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"VisualService: Error generating news card - {e}")
            return None
    def is_square(self, image_path: str, tolerance: float = 0.05) -> bool:
        """
        Checks if an image is roughly square (1:1 aspect ratio).
        """
        try:
            from PIL import Image
            img = Image.open(image_path)
            width, height = img.size
            ratio = width / height
            return (1.0 - tolerance) <= ratio <= (1.0 + tolerance)
        except Exception as e:
            logger.error(f"VisualService: Failed to check image ratio: {e}")
            return False

    def square_image(self, image_path: str, output_path: str = None) -> str:
        """
        Takes an image of any aspect ratio and places it on a 1:1 (square) 
        white canvas. This ensures Instagram compatibility.
        """
        try:
            from PIL import Image
            img = Image.open(image_path)
            
            width, height = img.size
            new_size = max(width, height)
            
            # Create white background
            new_img = Image.new("RGB", (new_size, new_size), (255, 255, 255))
            offset = ((new_size - width) // 2, (new_size - height) // 2)
            new_img.paste(img, offset)
            
            final_path = output_path or image_path.replace(".", "_squared.")
            new_img.save(final_path, quality=95)
            logger.info(f"VisualService: Squared image saved to {final_path}")
            return final_path
        except Exception as e:
            logger.error(f"VisualService: Failed to square image: {e}")
            return image_path
