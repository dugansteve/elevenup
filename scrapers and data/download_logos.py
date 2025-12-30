"""
Download club logos from various sources.
"""
import requests
import os
import time

LOGOS_DIR = r"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\App FrontEnd\Seedline_App\public\club_logos"

# Logos to download - (filename, url)
LOGOS_TO_DOWNLOAD = [
    # Legends FC
    ("Legends_FC_logo.png", "https://images.squarespace-cdn.com/content/v1/58b7589dc534a58cea04125e/1abf8677-c678-43f7-a4e5-427fb5d20cd1/legendsfc_full_logo_wht_web.png"),

    # LAFC So Cal Youth
    ("LAFC_So_Cal_Youth_logo.jpg", "https://images.mlssoccer.com/image/private/t_keep-aspect-ratio-e-mobile/f_auto/mls-lafc/atad6ug57emzifzjhafn.jpg"),

    # Orlando City SC (MLS logo)
    ("Orlando_City_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/ORL.svg"),

    # Beadling SC
    ("Beadling_SC_logo.png", "https://www.beadling.com/Portals/22889/logo638744761877770137.png"),

    # Total Futbol Academy
    ("Total_Futbol_Academy_logo.jpg", "https://cdn1.sportngin.com/attachments/photo/b14b-214873763/escut1_small.jpg"),

    # California Football Academy
    ("California_Football_Academy_logo.png", "https://clubs.bluesombrero.com/Portals/51595/logo638742210822499596.png"),

    # Austin FC
    ("Austin_FC_logo.svg", "https://images.mlssoccer.com/image/upload/v1595583232/assets/logos/ATX.svg"),

    # More MLS clubs (for youth teams)
    ("FC_Cincinnati_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/CIN.svg"),
    ("Charlotte_FC_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/CLT.svg"),
    ("Inter_Miami_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/MIA.svg"),
    ("Nashville_SC_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/NSH.svg"),
    ("St_Louis_City_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/STL.svg"),
    ("Atlanta_United_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/ATL.svg"),
    ("Houston_Dynamo_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/HOU.svg"),
    ("San_Jose_Earthquakes_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/SJ.svg"),
    ("LA_Galaxy_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/LA.svg"),
    ("New_York_Red_Bulls_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/RBNY.svg"),
    ("Philadelphia_Union_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/PHI.svg"),
    ("Portland_Timbers_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/POR.svg"),
    ("Seattle_Sounders_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/SEA.svg"),
    ("Sporting_KC_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/SKC.svg"),
    ("Columbus_Crew_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/CLB.svg"),
    ("DC_United_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/DC.svg"),
    ("Minnesota_United_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/MIN.svg"),
    ("Real_Salt_Lake_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/RSL.svg"),
    ("Vancouver_Whitecaps_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/VAN.svg"),
    ("Toronto_FC_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/TOR.svg"),
    ("CF_Montreal_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/MTL.svg"),
    ("New_England_Revolution_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/NE.svg"),
    ("Chicago_Fire_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/CHI.svg"),
    ("Colorado_Rapids_logo.svg", "https://images.mlssoccer.com/image/upload/assets/logos/COL.svg"),

    # Additional clubs
    ("Santa_Barbara_SC_logo.png", "https://santabarbarasc.org/wp-content/uploads/2021/07/2021-santa-barbara-soccer-club-logo.png"),

    # Strikers FC Irvine
    ("Strikers_FC_Irvine_logo.png", "https://images.squarespace-cdn.com/content/v1/62fad28c204b1f7cd775de24/30a108c0-d802-415d-98f4-0feb888efc12/STRIKERS+FC.png"),

    # Lancaster FC
    ("Lancaster_FC_logo.png", "https://images.squarespace-cdn.com/content/v1/677030af600a9a6ee4672abf/9f075583-ba34-433f-ab1a-9309200a067d/LancasterFC%28PNG-File%29-01.png"),

    # Mustang Soccer Club
    ("Mustang_SC_logo.png", "https://www.mustangsoccer.com/_templates/Home/images/logo.png"),

    # IMG Academy
    ("IMG_Academy_logo.png", "https://www.imgacademy.com/sites/default/files/imga-blue.png"),

    # FC Golden State
    ("FC_Golden_State_logo.png", "https://www.npsl.com/wp-content/uploads/2018/03/logo_FC-Golden-State-copy.png"),

    # De Anza Force
    ("De_Anza_Force_logo.png", "https://www.deanzaforce.org/_templates/Home/images/logo.png"),
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def download_logo(filename, url):
    """Download a logo and save it"""
    filepath = os.path.join(LOGOS_DIR, filename)

    if os.path.exists(filepath):
        print(f"  Already exists: {filename}")
        return True

    try:
        print(f"  Downloading: {filename}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            f.write(response.content)

        print(f"  Saved: {filename} ({len(response.content)} bytes)")
        return True
    except Exception as e:
        print(f"  Error downloading {filename}: {e}")
        return False

if __name__ == "__main__":
    print("Downloading club logos...")
    print(f"Output directory: {LOGOS_DIR}")
    print()

    success_count = 0
    for filename, url in LOGOS_TO_DOWNLOAD:
        if download_logo(filename, url):
            success_count += 1
        time.sleep(0.5)  # Be nice to servers

    print()
    print(f"Downloaded {success_count}/{len(LOGOS_TO_DOWNLOAD)} logos")
