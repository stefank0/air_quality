import time

import pandas as pd

from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    with open("write_request.temp", "w") as _:
        pass
    time.sleep(3)
    df = pd.read_csv('data.csv', header=None)
    context = {"time": list(df[0]), "temperature": list(df[1]), "humidity": list(df[2])}
    return render(request, 'air_quality.html', context)

