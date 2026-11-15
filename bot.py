import os
import io
import logging
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import (
    Application,
    ChatMemberHandler,
    ContextTypes
)

# ========== SETTINGS ==========

BOT_TOKEN = os.environ["BOT_TOKEN"]

TEMPLATE = "welcome_template.png"
USERNAME_FONT = "fonts/Poppins-Bold.ttf"

# Username position
NAME_X = 950
NAME_Y = 145
MAX_NAME_WIDTH = 500

# Profile circle position
PHOTO_X = 105
PHOTO_Y = 215
PHOTO_SIZE = 450

logging.basicConfig(level=logging.INFO)


# ========== WELCOME IMAGE ==========

async def create_welcome(update, context):

    member = update.chat_member.new_chat_member.user
    chat = update.effective_chat

    if member.is_bot:
        return

    name = member.full_name

    img = Image.open(TEMPLATE).convert("RGBA")

    # Download profile photo
    photos = await context.bot.get_user_profile_photos(
        member.id, limit=1
    )

    if photos.total_count > 0:

        photo_file = await context.bot.get_file(
            photos.photos[0][-1].file_id
        )

        photo_bytes = io.BytesIO()
        await photo_file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)

        profile = Image.open(photo_bytes).convert("RGB")

        # Square crop
        w, h = profile.size
        crop = min(w, h)

        left = (w - crop) // 2
        top = (h - crop) // 2

        profile = profile.crop(
            (left, top, left + crop, top + crop)
        )

        profile = profile.resize(
            (PHOTO_SIZE, PHOTO_SIZE),
            Image.Resampling.LANCZOS
        )

        # Circle mask
        mask = Image.new(
            "L", (PHOTO_SIZE, PHOTO_SIZE), 0
        )

        ImageDraw.Draw(mask).ellipse(
            (0, 0, PHOTO_SIZE, PHOTO_SIZE),
            fill=255
        )

        img.paste(
            profile,
            (PHOTO_X, PHOTO_Y),
            mask
        )

    # Dynamic username
    draw = ImageDraw.Draw(img)

    font_size = 76

    while font_size > 15:
        font = ImageFont.truetype(
            USERNAME_FONT, font_size
        )

        bbox = draw.textbbox((0, 0), name, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= MAX_NAME_WIDTH:
            break

        font_size -= 2

    # Center username
    x = NAME_X - text_width // 2 - bbox[0]
    y = NAME_Y - bbox[1]

    draw.text(
        (x, y),
        name,
        font=font,
        fill="#FFFFFF"
    )

    # Export image
    output = io.BytesIO()

    img.convert("RGB").save(
        output,
        format="JPEG",
        quality=95
    )

    output.seek(0)
    output.name = "welcome.jpg"

    # Send welcome image
    await context.bot.send_photo(
        chat_id=chat.id,
        photo=output
    )


# ========== JOIN DETECTION ==========

async def member_update(update: Update,
                        context: ContextTypes.DEFAULT_TYPE):

    result = update.chat_member

    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    if (
        new_status in ("member", "administrator")
        and old_status in ("left", "kicked")
    ):
        await create_welcome(update, context)


# ========== START BOT ==========

def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        ChatMemberHandler(
            member_update,
            ChatMemberHandler.CHAT_MEMBER
        )
    )

    print("Welcome Bot Started!")

    app.run_polling(
        allowed_updates=["chat_member"]
    )


if __name__ == "__main__":
    main()
