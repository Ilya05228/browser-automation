#!/usr/bin/env python3
"""
Создание иконки для приложения.
Требуется установленный Pillow: pip install pillow
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    # Создаём простую иконку 256x256
    size = 256
    img = Image.new('RGBA', (size, size), (26, 115, 232, 255))  # Синий фон
    draw = ImageDraw.Draw(img)
    
    # Рисуем круг
    draw.ellipse([20, 20, size-20, size-20], fill=(255, 255, 255, 255))
    
    # Рисуем камеру (упрощённо)
    # Объектив
    draw.ellipse([80, 80, 176, 176], fill=(26, 115, 232, 255))
    draw.ellipse([96, 96, 160, 160], fill=(255, 255, 255, 255))
    
    # Вспышка
    draw.rectangle([180, 60, 210, 90], fill=(255, 255, 255, 255))
    
    # Сохраняем в разных форматах
    img.save('icon.png', 'PNG')
    
    # Для Windows нужен .ico
    # Создаём несколько размеров для .ico
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_images = []
    
    for w, h in sizes:
        resized = img.resize((w, h), Image.Resampling.LANCZOS)
        icon_images.append(resized)
    
    # Сохраняем как .ico
    if len(icon_images) > 0:
        icon_images[0].save('icon.ico', format='ICO', sizes=[(img.width, img.height) for img in icon_images])
    
    print("✅ Иконки созданы:")
    print("   - icon.png (256x256)")
    print("   - icon.ico (для Windows)")
    
except ImportError:
    print("⚠️  Pillow не установлен. Установите: pip install pillow")
    print("📝 Создаю placeholder иконки...")
    
    # Создаём пустые файлы-заглушки
    with open('icon.png', 'wb') as f:
        f.write(b'')
    with open('icon.ico', 'wb') as f:
        f.write(b'')
    
    print("✅ Файлы-заглушки созданы")
    print("💡 Для создания настоящих иконок установите Pillow: pip install pillow")