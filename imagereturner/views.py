from django.http import JsonResponse, HttpResponse
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from django.http import FileResponse
import uuid
import random
import requests
import json
import os
import platform
import time

access_token = "94b8c4c694b8c4c694b8c4c68894c2ab6e994b894b8c4c6f50b01863e04926b911fb650"


def vk_search(phrase, token):
    result = requests.get(url= "https://api.vk.com/method/photos.search", params={
        'q': f"{phrase} -цена -руб -₽ -оплата",
        'access_token': token,
        'v': '5.81',
        })
    if items := json.loads(result.text)["response"]["items"]:
        result = sorted(random.choice(items)["sizes"], key=lambda x: x["height"], reverse=True)[0]["url"]
        return result
    return None


def resizer(image_name):
    pil_image = Image.open(image_name).resize((1000, 1000)).convert('RGB')
    return pil_image


def get_label(phrase):
    font_size = random.randint(100, 300)
    random_font_file = random.choice(os.listdir("imagereturner/fonts"))
    font = ImageFont.truetype(f"imagereturner/fonts/{random_font_file}", font_size)
    string_size_in_pixels = font.getsize(phrase)
    label = Image.new(size=string_size_in_pixels, mode="RGBA")
    ImageDraw.Draw(label).text((0, 0), phrase,
                                   (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
                                   font=font)
    return [label, string_size_in_pixels]


def creation_date(path_to_file):
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime


def delete_old_files(filename):
    file_path = "trash/" + filename
    date_in_ms = creation_date(file_path)
    if int(time.time()) -date_in_ms > 60:
        os.remove(file_path)
    return date_in_ms


def return_image(request):
    if request.method == "POST":

        downloaded_files = os.listdir("trash")
        list(map(delete_old_files, downloaded_files))
        request = json.loads(request.body)
        phrase = request["phrase"]
        print(phrase)
        tags = request["tags"]
        result = vk_search(phrase, access_token)
        if result:
            img_data = requests.get(result).content
            name = f"trash/{uuid.uuid4()}.png"
            with open(name, 'wb') as handler:
                handler.write(img_data)
            pil_image = resizer(image_name=name)
            phrase_label, size = get_label(phrase)
            if size[0] > 1000:
                wight = random.randint(800, 900)
                height = int(size[1]*wight/size[0])
                phrase_label = phrase_label.resize((wight, height))
                pil_image.paste(phrase_label, (random.randint(0, 1000 - wight), random.randint(0, 1000 - height)),
                                phrase_label.convert("RGBA"))
            else:
                pil_image.paste(phrase_label, (random.randint(0, 1000-size[0]), random.randint(0, 1000-size[1])), phrase_label.convert("RGBA"))
            pil_image.save(name)
            return FileResponse(open(name, "rb"))
        return HttpResponse(status=404)
