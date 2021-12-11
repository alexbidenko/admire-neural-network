from django.http import JsonResponse, HttpResponse
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from django.http import FileResponse
import uuid
import random
import requests
import json
import os

access_token = "94b8c4c694b8c4c694b8c4c68894c2ab6e994b894b8c4c6f50b01863e04926b911fb650"


def vk_search(phrase, token):
    result = requests.get(url= "https://api.vk.com/method/photos.search", params= {
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


def return_image(request):
    if request.method == "POST":
        request = json.loads(request.body)
        phrase = request["phrase"]
        print(phrase)
        tags = request["tags"]
        random_font_file = random.choice(os.listdir("imagereturner/fonts"))
        print(random_font_file)
        font = ImageFont.truetype(f"imagereturner/fonts/{random_font_file}", random.randint(50, 200))
        result = vk_search(phrase, access_token)
        if result:
            img_data = requests.get(result).content
            name = f"{uuid.uuid4()}.png"
            with open(name, 'wb') as handler:
                handler.write(img_data)
            pil_image = resizer(image_name=name)
            ImageDraw.Draw(pil_image).text((random.randint(100, 900), random.randint(100, 900)), phrase,
                                           (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
                                           font=font)
            pil_image.save(name)
            return FileResponse(open(name, "rb"))
        return HttpResponse(status=404)
