import locale
from django.shortcuts import render
from django.http import JsonResponse
import requests
import os
import json

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

def verificar_cidade(endereco):
    if isinstance(endereco, str):
        return "belo horizonte" in endereco.lower()
    return False


def calcular_distancias(enderecos):
    distancias = []
    total_km = 0
    entregas_bh = 0
    deslocamento_sede = fetch_distance(SEDE, enderecos[0])
    
    if deslocamento_sede is None:
        return None, "Erro ao calcular a distância para o primeiro endereço."
    
    total_km += deslocamento_sede
    distancias.append({
        "origem": SEDE,
        "destino": enderecos[0],
        "distancia": format_distance(deslocamento_sede)
    })

    if verificar_cidade(enderecos[0]):
        entregas_bh += 1

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
        if verificar_cidade(enderecos[i]):
            entregas_bh += 1

    # Ajuste para a sede e segundo endereço
    if len(enderecos) > 1:
        distancia_segundo = fetch_distance(SEDE, enderecos[1])
        if distancia_segundo and (distancia_segundo < 3.6 or deslocamento_sede < 3.6):
            total_km -= deslocamento_sede

    return total_km, distancias, entregas_bh  

def format_distance(km):
    return "{:.1f}".format(km).replace(',', '.')

def calcular_custo(modulo, total_km, num_enderecos, entregas_bh, enderecos, volume=False, tempo_parado=0):
    fora_bh = any(not verificar_cidade(endereco) for endereco in enderecos)
    if modulo == "MOTO":
        if total_km <= 2:
            custo = 18.00  # Até 2 km
        elif 2 < total_km <= 10:
            custo = 18.00 + total_km * 1.20  # De 2 km até 10 km
        else:
            # Acima de 10 km
            if fora_bh:
                custo = 18.00 + total_km * 1.65  # Fora de Belo Horizonte
            else:
                custo = 18.00 + total_km * 1.35  # Dentro de Belo Horizonte
        if volume: #Adiciona 10 reais caso tenha Volume
            custo += 10.00
        if num_enderecos > 2:
            custo_adicional = (num_enderecos - 2) * 10  # 10 reais por endereço após o segundo
            custo += custo_adicional
            
    elif modulo == "CARRO":
        custo = 80.00
        if total_km > 8:
            custo += (total_km - 8) * 2.90
        if total_km > 90:
            custo *= 2.20

    # Calcular o custo do tempo parado (se houver)
    if tempo_parado > 0:
        custo_tempo_parado = (tempo_parado / 60) * 25.00  # R$ 25 por hora, fração proporcional
        custo += custo_tempo_parado

    custo_formatado = locale.currency(custo, grouping=True, symbol=True)
    return custo_formatado
    
def calculo(request):
    if request.method == "POST":
        modulo = request.POST.get("modulo")
        enderecos = request.POST.getlist("enderecos[]")
        volume = request.POST.get("volume")
        tempo_parado = request.POST.get("tempo_parado", 0)  # Captura o tempo parado (em minutos)

         # Se o campo tempo_parado estiver vazio, define como 0
        if not tempo_parado:
            tempo_parado = 0

        # Verifica se o volume foi selecionado (obrigatório)
        if volume is None:
            return render(request, "calculo.html", {"erro": "Por favor, selecione se o volume está presente ou não."})
        
        # Converte o campo volume para booleano
        volume = volume == "on"
        veiculo = request.POST.get('modulo', 'Não especificado')

        # Verifica se o modulo e endereços foram preenchidos
        if not modulo:
            return render(request, "calculo.html", {"erro": "Por favor, selecione um tipo de veículo."})
        if not enderecos:
            return render(request, "calculo.html", {"erro": "Por favor, insira ao menos um endereço."})

        if enderecos:
            total_km, distancias, entregas_bh = calcular_distancias(enderecos)
            if total_km is None:
                return render(request, "calculo.html", {"erro": distancias})
            
            custo_total = calcular_custo(modulo, total_km, len(enderecos), entregas_bh, enderecos, volume=volume, tempo_parado=int(tempo_parado))

            distancias_formatadas = [d for i, d in enumerate(distancias) if i != 0]
            total_km_formatada = format_distance(total_km)

            return render(request, "resultado.html", {
                'veiculo': veiculo,
                "custo_total": custo_total,
                "total_km": total_km_formatada,
                "distancias": distancias_formatadas,
                "entregas_bh": entregas_bh,
                "volume": "Sim" if volume else "Não",
                "tempo_parado": tempo_parado
            })
    return render(request, "calculo.html")
