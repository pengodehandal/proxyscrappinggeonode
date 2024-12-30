import requests
import json
import socket
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

# Fungsi untuk mengambil proxy dari API GeoNode
def grab_proxies():
    proxies = []
    page = 1
    while True:
        # Membuat URL dengan nomor halaman yang dinamis
        url = f"https://proxylist.geonode.com/api/proxy-list?limit=500&page={page}&sort_by=lastChecked&sort_type=desc"
        
        # Mengambil data dari API
        response = requests.get(url)
        
        # Cek jika halaman berhasil diambil
        if response.status_code != 200:
            print(f"Gagal mengambil data pada halaman {page}. Status code: {response.status_code}")
            break

        # Coba untuk parsing JSON
        try:
            proxies_data = response.json()
        except json.JSONDecodeError as e:
            print(f"Error saat parsing JSON pada halaman {page}: {e}")
            print("Isi response:", response.text)  # Menampilkan response mentah
            break

        # Memastikan data yang diterima adalah dictionary dengan kunci yang relevan
        if isinstance(proxies_data, dict):
            proxies_list = proxies_data.get("data", [])
        else:
            print(f"Data tidak dalam format yang diharapkan pada halaman {page}. Ditemukan: {type(proxies_data)}")
            break

        # Jika tidak ada proxy, berhenti
        if not proxies_list:
            print(f"Tidak ada proxy lagi pada halaman {page}. Menghentikan pengambilan.")
            break

        # Menambahkan proxy yang ditemukan ke dalam daftar
        for proxy in proxies_list:
            ip = proxy.get("ip")
            port = proxy.get("port")
            if ip and port:
                proxies.append(f"{ip}:{port}")

        print(f"Berhasil mengambil proxy dari halaman {page}, total proxy yang diambil: {len(proxies)}.")
        
        # Pindah ke halaman berikutnya
        page += 1

    return proxies

# Fungsi untuk memeriksa status proxy menggunakan socket
def check_proxy_active(proxy):
    ip, port = proxy.split(":")
    try:
        # Membuat socket untuk mencoba menghubungi proxy
        proxy_socket = socket.create_connection((ip, int(port)), timeout=5)
        proxy_socket.close()
        return True
    except Exception as e:
        return False

# Fungsi untuk memeriksa jenis proxy menggunakan aiohttp
async def get_proxy_type(session, proxy):
    ip, port = proxy.split(":")
    try:
        # Gunakan URL alternatif untuk memeriksa proxy
        test_url = "https://httpstat.us/200"  # URL ringan yang selalu memberikan status 200 OK
        async with session.get(test_url, proxy=f"http://{ip}:{port}", timeout=5) as response:
            if response.status == 200:
                return proxy, "http"
            else:
                return proxy, "unknown"
    except Exception:
        return proxy, "unknown"

# Fungsi untuk memeriksa proxy dan menyimpannya berdasarkan jenisnya menggunakan Asynchronous Requests
async def proxy_checker(proxies):
    proxies_by_type = {
        "http": [],
        "socks4": [],
        "socks5": [],
        "https": []
    }

    async with aiohttp.ClientSession() as session:
        tasks = []
        for proxy in proxies:
            # Membuat task untuk setiap proxy
            tasks.append(asyncio.ensure_future(get_proxy_type(session, proxy)))

        results = await asyncio.gather(*tasks)  # Menjalankan semua task secara paralel

        # Mengkategorikan proxy berdasarkan jenisnya
        for result in results:
            proxy, proxy_type = result
            if proxy_type != "unknown":
                proxies_by_type[proxy_type].append(proxy)

    # Menyimpan proxy berdasarkan jenisnya
    save_proxy_by_type(proxies_by_type)

# Fungsi untuk menyimpan proxy berdasarkan jenisnya
def save_proxy_by_type(proxies_by_type):
    for proxy_type, proxies in proxies_by_type.items():
        if proxies:
            file_name = f"{proxy_type}.txt"
            with open(file_name, "w") as file:
                for proxy in proxies:
                    file.write(proxy + "\n")
            print(f"Proxy jenis {proxy_type} berhasil disimpan ke {file_name}")

# Fungsi untuk membaca proxy dari file
def read_proxies_from_file(file_name):
    try:
        with open(file_name, "r") as file:
            proxies = [line.strip() for line in file.readlines()]
        return proxies
    except FileNotFoundError:
        print(f"File {file_name} tidak ditemukan.")
        return []

# Fungsi untuk menyimpan proxy ke dalam file
def save_proxies_to_file(proxies):
    with open("proxygrab.txt", "w") as file:
        for proxy in proxies:
            file.write(proxy + "\n")

# Fungsi utama
def main():
    # Menu utama
    print("1. Hanya ambil proxy (dari file GeoNode)")
    print("2. Ambil proxy dan cek status proxy (dari file GeoNode)")
    print("3. Proxy Checker (cek proxy dari file yang sudah ada)")
    choice = input("Pilih opsi (1/2/3): ")

    if choice == "1":
        # Ambil proxy dari GeoNode
        proxies = grab_proxies()
        if proxies:
            # Menyimpan proxy ke dalam file
            save_proxies_to_file(proxies)
            print(f"Berhasil mengambil {len(proxies)} proxy dari geonode.com.")
        else:
            print("Tidak ada proxy yang ditemukan.")
    
    elif choice == "2":
        # Ambil proxy dari GeoNode dan cek statusnya
        proxies = grab_proxies()
        if proxies:
            # Menyimpan proxy ke dalam file
            save_proxies_to_file(proxies)
            print(f"Berhasil mengambil {len(proxies)} proxy dari geonode.com.")
            print("Mulai mengecek proxy...")
            asyncio.run(proxy_checker(proxies))
        else:
            print("Tidak ada proxy yang ditemukan.")
    
    elif choice == "3":
        # Proxy Checker dari file
        file_name = input("Masukkan nama file proxy yang akan di cek (misal: proxygrab.txt): ").strip()
        proxies = read_proxies_from_file(file_name)
        if proxies:
            print("Mulai mengecek proxy...")
            asyncio.run(proxy_checker(proxies))
        else:
            print("Tidak ada proxy yang ditemukan di file.")
    else:
        print("Pilihan tidak valid.")

if __name__ == "__main__":
    main()
