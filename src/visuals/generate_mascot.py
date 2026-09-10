import math
from pathlib import Path
from PIL import Image, ImageDraw

def create_default_fish_sprites(output_dir: Path):
    """
    Generates high-res transparent PNGs for the fish news anchor:
    - fish_closed.png (mouth shut / confident news smile)
    - fish_open.png (mouth wide open delivering breaking news)
    Users can also overwrite these files with their own custom art anytime!
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    closed_path = output_dir / "fish_closed.png"
    open_path = output_dir / "fish_open.png"

    def draw_base_anchor():
        # Canvas: 600x600 transparent
        img = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 1. Dark Blue Anchor Suit (Shoulders)
        # Suit polygon at bottom
        suit_color = (25, 42, 86, 255) # Deep navy
        suit_points = [(100, 600), (160, 390), (440, 390), (500, 600)]
        draw.polygon(suit_points, fill=suit_color)
        draw.line(suit_points, fill=(15, 25, 55, 255), width=5)

        # White Shirt Collar
        shirt_color = (245, 246, 250, 255)
        draw.polygon([(260, 390), (300, 480), (340, 390)], fill=shirt_color)

        # Red Tie
        tie_color = (232, 65, 24, 255)
        draw.polygon([(288, 410), (312, 410), (320, 560), (300, 590), (280, 560)], fill=tie_color)

        # Lapels on suit
        draw.polygon([(160, 390), (250, 470), (220, 530)], fill=(35, 55, 110, 255))
        draw.polygon([(440, 390), (350, 470), (380, 530)], fill=(35, 55, 110, 255))

        # 2. Fish Head (Classic SpongeBob Olive/Greenish Fish tone)
        head_color = (130, 180, 64, 255)   # Olive green
        head_outline = (70, 110, 30, 255)
        # Head oval
        draw.ellipse([170, 140, 430, 410], fill=head_color, outline=head_outline, width=6)

        # Dorsal fin / side fin
        fin_color = (160, 210, 80, 255)
        draw.polygon([(180, 160), (140, 100), (220, 130)], fill=fin_color, outline=head_outline, width=4)
        draw.polygon([(420, 160), (460, 100), (380, 130)], fill=fin_color, outline=head_outline, width=4)

        # Big Cartoon Eyes (Classic sideways fish eyes)
        # Left Eye
        draw.ellipse([180, 170, 280, 270], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=5)
        draw.ellipse([215, 200, 250, 235], fill=(20, 20, 20, 255)) # Pupil
        draw.ellipse([222, 205, 235, 218], fill=(255, 255, 255, 255)) # Eye shine

        # Right Eye
        draw.ellipse([320, 170, 420, 270], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=5)
        draw.ellipse([350, 200, 385, 235], fill=(20, 20, 20, 255)) # Pupil
        draw.ellipse([357, 205, 370, 218], fill=(255, 255, 255, 255)) # Eye shine

        # Eyebrows (Expressive anchor eyebrows)
        draw.line([(190, 160), (260, 175)], fill=(40, 70, 20, 255), width=7)
        draw.line([(410, 160), (340, 175)], fill=(40, 70, 20, 255), width=7)

        # Gills
        draw.arc([190, 280, 220, 340], start=80, end=270, fill=(70, 110, 30, 255), width=4)
        draw.arc([380, 280, 410, 340], start=270, end=100, fill=(70, 110, 30, 255), width=4)

        # Classic News Anchor Microphone at the bottom left
        mic_color = (60, 64, 67, 255)
        draw.rectangle([210, 480, 230, 600], fill=mic_color)
        draw.ellipse([200, 440, 240, 490], fill=(120, 120, 120, 255), outline=(30, 30, 30, 255), width=3)
        draw.line([(205, 465), (235, 465)], fill=(40, 40, 40, 255), width=2)

        return img, draw

    # --- Generate CLOSED MOUTH ---
    img_closed, draw_closed = draw_base_anchor()
    # Confident news anchor smile
    draw_closed.arc([240, 290, 360, 360], start=20, end=160, fill=(40, 20, 20, 255), width=6)
    draw_closed.line([(235, 315), (245, 310)], fill=(40, 20, 20, 255), width=5)
    draw_closed.line([(355, 310), (365, 315)], fill=(40, 20, 20, 255), width=5)
    img_closed.save(closed_path)

    # --- Generate OPEN MOUTH ---
    img_open, draw_open = draw_base_anchor()
    # Wide open shouting/reporting mouth
    mouth_box = [245, 295, 355, 385]
    draw_open.ellipse(mouth_box, fill=(50, 15, 20, 255), outline=(40, 10, 15, 255), width=5)
    # Pink tongue
    draw_open.ellipse([260, 345, 340, 385], fill=(235, 90, 120, 255))
    # Top white cartoon teeth
    draw_open.rectangle([275, 298, 295, 315], fill=(255, 255, 255, 255), outline=(40, 10, 15, 255), width=2)
    draw_open.rectangle([305, 298, 325, 315], fill=(255, 255, 255, 255), outline=(40, 10, 15, 255), width=2)
    img_open.save(open_path)

    print(f"Generated fish anchor sprites:\n- {closed_path}\n- {open_path}")

if __name__ == "__main__":
    from ..config import SPRITES_DIR
    create_default_fish_sprites(SPRITES_DIR)
