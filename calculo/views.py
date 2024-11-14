import locale
from django.shortcuts import render
from django.http import JsonResponse
import requests
import os

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
SEDE = "Rua dos Guajajaras, 1470 - Barro Preto, Belo Horizonte - MG, Brasil"
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyAGiBjDqNIkqx5bqv3wlqPO2wcIQ2wZqN0")
BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

def fetch_distance(origin, destination):
    try:
        response = requests.get(BASE_URL, params={
            "origins": origin,
            "destinations": destination,
            "key": API_KEY
        })
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'OK' and 'distance' in data['rows'][0]['elements'][0]:
            return data['rows'][0]['elements'][0]['distance']['value'] / 1000  # Em quilômetros
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar distância: {e}")
    return None

def calcular_distancias(enderecos):
    distancias = []
    total_km = 0
    deslocamento_sede = fetch_distance(SEDE, enderecos[0])
    
    if deslocamento_sede is None:
        return None, "Erro ao calcular a distância para o primeiro endereço."
    
    total_km += deslocamento_sede
    distancias.append({
        "origem": SEDE,
        "destino": enderecos[0],
        "distancia": format_distance(deslocamento_sede)
    })

    for i in range(1, len(enderecos)):
        distancia = fetch_distance(enderecos[i - 1], enderecos[i])
        if distancia is None:
            return None, f"Erro ao calcular a distância para o endereço {i}"
        total_km += distancia
        distancias.append({
            "origem": enderecos[i - 1],
            "destino": enderecos[i],
            "distancia": format_distance(distancia)
        })

    # Ajuste para a sede e segundo endereço
    if len(enderecos) > 1:
        distancia_segundo = fetch_distance(SEDE, enderecos[1])
        if distancia_segundo and (distancia_segundo < 3.6 or deslocamento_sede < 3.6):
            total_km -= deslocamento_sede

    return total_km, distancias

def format_distance(km):
    return "{:.1f}".format(km).replace(',', '.')

def calcular_custo(modulo, total_km, num_enderecos):
    if modulo == "MOTO":
        custo = 18.00 + total_km * 1.30
        if num_enderecos > 2:
            extra_cost = 10.00 if 1 < total_km <= 18 else 20.00
            custo += (num_enderecos - 2) * extra_cost
        if total_km > 100:
            custo *= 2
    elif modulo == "CARRO":
        custo = 80.00
        if total_km > 8:
            custo += (total_km - 8) * 2.60
        if total_km > 90:
            custo *= 2
    custo_formatado = locale.currency(custo, grouping=True, symbol=True)
    return custo_formatado
    
def calculo(request):
    if request.method == "POST":
        modulo = request.POST.get("modulo")
        enderecos = request.POST.getlist("enderecos[]")
        veiculo = request.POST.get('modulo', 'Não especificado')

        if enderecos:
            total_km, distancias = calcular_distancias(enderecos)
            if total_km is None:
                return render(request, "calculo.html", {"erro": distancias})
            
            custo_total = calcular_custo(modulo, total_km, len(enderecos))
            distancias_formatadas = [d for i, d in enumerate(distancias) if i != 0]
            total_km_formatada = format_distance(total_km)

            return render(request, "resultado.html", {
                'veiculo': veiculo,
                "custo_total": custo_total,
                "total_km": total_km_formatada,
                "distancias": distancias_formatadas
            })
    return render(request, "calculo.html")
