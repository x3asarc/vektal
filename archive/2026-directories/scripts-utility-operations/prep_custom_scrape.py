import re
import pandas as pd
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
SHOP_DOMAIN = os.getenv("SHOP_DOMAIN")
API_VERSION = os.getenv("API_VERSION", "2024-01")
TOKEN_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/oauth/access_token"
GRAPHQL_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json"

raw_input = """
Reispapier - Barber Gentleman A5 oder A4
ID: 10299077132626
Reispapier - Easter Bunnies
ID: 6665809166493
Reispapier - Gentleman Stil A5 oder A4
ID: 10299076542802
Reispapier - Merry Christmas fröhliche Tierweihnacht
ID: 10298881278290
Reispapier - Philodendron Monstera
ID: 10224073933138
Reispapier - White flower A4
ID: 6666205036701
Reispapier - wilde Enten A5 oder A4
ID: 10350060732754
Reispapier -Jobs Schneiderin Mode A5 oder A4
ID: 10297868321106
Reispapier -Jobs Schneiderin Mode A5 oder A4
ID: 10297868517714
Reispapier 32x45cm - Angels and roses
ID: 6665978019997
Reispapier 32x45cm - Winter joy rounds
ID: 7860873527512
Reispapier A3 - A peaceful christmas 4.
ID: 6665938469021
Reispapier A3 - Alice Magic
ID: 10297590251858
Reispapier A3 - Angelic faces
ID: 7943425917144
Reispapier A3 - Best friends
ID: 7874489450712
Reispapier A3 - Christmas carols
ID: 7831766565080
Reispapier A3 - Daisy
ID: 8642726003026
Reispapier A3 - Dance
ID: 7594194960600
Reispapier A3 - Discovery
ID: 8358650413394
Reispapier A3 - Funny Santa
ID: 7860605878488
Reispapier A3 - Funny Santa rounds
ID: 7860598374616
Reispapier A3 - Into the wild - A walk in the forest
ID: 8554623992146
Reispapier A3 - Into the wild - Boreal nature
ID: 8556275794258
Reispapier A3 - Japanese lion
ID: 8642304737618
Reispapier A3 - Lady Elisabeth
ID: 8358648217938
Reispapier A3 - Lion portrait
ID: 8642741633362
Reispapier A3 - Mediterranean tiles
ID: 6666289741981
Reispapier A3 - Millefiori
ID: 8642682618194
Reispapier A3 - Motorcycles
ID: 7594200432856
Reispapier A3 - Old airplanes 1.
ID: 7637739241688
Reispapier A3 - Old photos
ID: 7594176217304
Reispapier A3 - Ponte vecchio
ID: 7772426961112
Reispapier A3 - Still life with cotton
ID: 7777559609560
Reispapier A3 - Stone flowers
ID: 8642685665618
Reispapier A3 - Summer pin up
ID: 7594190536920
Reispapier A3 - Views
ID: 7594209870040
Reispapier A3 - Village everyday
ID: 7594216718552
Reispapier A3 - Vintage photos
ID: 7594182344920
Reispapier A3 - Wild Rabbits
ID: 7943426408664
Reispapier A3 - Winter Bouquet 1
ID: 8942766948690
Reispapier A3 - Winter dreamland village
ID: 6665917005981
Reispapier A3 - Winter views
ID: 6666177380509
Reispapier A3 - Winter walk frames
ID: 7861025669336
Reispapier A3 - Winter wreaths small
ID: 8610726314322
Reispapier A3 - Zendaya
ID: 7664514269400
Reispapier A4 - A peaceful christmas 2.
ID: 6665932177565
Reispapier A4 - Alchemy rounds
ID: 8487683817810
Reispapier A4 - All around Christmas - 4 cards
ID: 8570428850514
Reispapier A4 - All around Christmas - 6 garlands
ID: 8570428358994
Reispapier A4 - All around Christmas - Garlands with cat
ID: 8570421018962
Reispapier A4 - All around Christmas - Red door
ID: 8570425737554
Reispapier A4 - All around Christmas - Sweet room
ID: 8570404995410
Reispapier A4 - American eagle
ID: 6666288791709
Reispapier A4 - Around the world - Map
ID: 8507852095826
Reispapier A4 - Around the world - Sailing ship
ID: 8507843379538
Reispapier A4 - Best friends
ID: 8931961078098
Reispapier A4 - Christmas greetings - Flower
ID: 8571950956882
Reispapier A4 - Christmas joy children
ID: 7524542742744
Reispapier A4 - Christmas stores
ID: 8610579677522
Reispapier A4 - Classic Christmas Santa Claus
ID: 6951898316957
Reispapier A4 - Collateral rust
ID: 6666136256669
Reispapier A4 - Cosmos infinity rounds
ID: 7813984911576
Reispapier A4 - Cozy time
ID: 7879522222296
Reispapier A4 - Easter eggs with flowers
ID: 7596981420248
Reispapier A4 - Enchanted land - Spread the wings
ID: 8478536859986
Reispapier A4 - Fantastic creatures
ID: 7831858118872
Reispapier A4 - Flowers on board
ID: 8455309328722
Reispapier A4 - Frozen roses medallions
ID: 6666175578269
Reispapier A4 - Happy easter bouquet
ID: 6665809821853
Reispapier A4 - Herbst
ID: 8838384484690
Reispapier A4 - Home decorations
ID: 7831772561624
Reispapier A4 - Home decorations
ID: 9691750138194
Reispapier A4 - Jetty
ID: 6747544551581
Reispapier A4 - Lavande de Provence 2.
ID: 8523916771666
Reispapier A4 - Magic Forest Amazon
ID: 8364426658130
Reispapier A4 - Magister Rabbit with wife
ID: 6666270179485
Reispapier A4 - Miniature old portraits
ID: 8788854636882
Reispapier A4 - Northern lights
ID: 6666175185053
Reispapier A4 - Old western chariot
ID: 8357487313234
Reispapier A4 - Perfection
ID: 7734620389592
Reispapier A4 - Plein d´orange
ID: 7858042962136
Reispapier A4 - Queen lore
ID: 7959038492888
Reispapier A4 - Red brocade
ID: 7091510083741
Reispapier A4 - Ripe grapes
ID: 7858043322584
Reispapier A4 - Romantic Horses lady frame
ID: 6951969456285
Reispapier A4 - Romantic Horses running horse
ID: 6951967981725
Reispapier A4 - Sir Vagabond in Japan samurai
ID: 6951828029597
Reispapier A4 - Sleeping Beauty cradle
ID: 6951909327005
Reispapier A4 - Spring all over
ID: 6665986277533
Reispapier A4 - Sunflower Art - Landscape
ID: 8502396027218
Reispapier A4 - Sunflower Art - Shop
ID: 8502395339090
Reispapier A4 - Sunflower Art - Vintage car
ID: 8502397862226
Reispapier A4 - Sunflower Art - Window
ID: 8502392553810
Reispapier A4 - Sunflower Art and horses
ID: 8502390653266
Reispapier A4 - Teerosen
ID: 6665489645725
Reispapier A4 - The sound of autumn
ID: 6665982640285
Reispapier A4 - The world changes when it snows
ID: 6666136780957
Reispapier A4 - Tuscan dream
ID: 6665983918237
Reispapier A4 - Under the tuscan sun cards
ID: 6665983754397
Reispapier A4 - Vintage easter bunnies
ID: 8341090238802
Reispapier A4 - Vintage photos
ID: 8515366224210
Reispapier A4 - Vintage Woman
ID: 8838393266514
Reispapier A4 - Vögel
ID: 8847539798354
Reispapier A4 - Vögel
ID: 9839100166482
Reispapier A4 - Vögel
ID: 10214663356754
Reispapier A4 - Waiting for Santa
ID: 10356039876946
Reispapier A4 - Waiting for Santa
ID: 10356074217810
Reispapier A4 - Waiting for Santa
ID: 10356091879762
Reispapier A4 - Waiting for Santa
ID: 10356101022034
Reispapier A4 - Waiting for Santa
ID: 10356112326994
Reispapier A4 - Waiting for Santa
ID: 10356113736018
Reispapier A4 - Waiting for Santa
ID: 10356136837458
Reispapier A4 - Waiting for Santa
ID: 10356147749202
Reispapier A4 - Waiting for Santa
ID: 10356176519506
Reispapier A4 - Waiting for Santa
ID: 10356190314834
Reispapier A4 - Waiting for Santa
ID: 10356201750866
Reispapier A4 - Waiting for Santa
ID: 10356208599378
Reispapier A4 - Waiting for Santa
ID: 10356215415122
Reispapier A4 - Weihnachten anno
ID: 6665609314461
Reispapier A4 - White garlands
ID: 7831771349208
Reispapier A4 - Winter
ID: 8838379602258
Reispapier A4 - Winter tales poinsettia
ID: 6951848018077
Reispapier A4 - Winter Valley - 4 cards fox
ID: 8565152153938
Reispapier A4 - Winter valley - Family garlands
ID: 8571216855378
Reispapier A4 - Winter valley - Fox and bunny
ID: 8571214561618
Reispapier A4 - Winter Valley - Joy birds
ID: 8565150450002
Reispapier A4 - Winter Valley - Rounds
ID: 8565149827410
Reispapier A4 - Winter valley - Sweet night
ID: 8571213119826
Reispapier A4 - Woodland butterfly
ID: 8681984295250
Reispapier A4 - Woodland rounds
ID: 8681982525778
Reispapier Pferd A5 oder A4
ID: 10297950372178
Reispapier Pferde A5 oder A4
ID: 10297953747282
"""

# Extract IDs and Titles
matches = re.finditer(r"^(.*?)\nID: (\d+)", raw_input, re.MULTILINE)
data = []
seen_ids = set()

for m in matches:
    title = m.group(1).strip()
    pid = m.group(2).strip()
    if pid in seen_ids:
        print(f"Skipping duplicate ID: {pid}")
        continue
    seen_ids.add(pid)
    data.append({"Title": title, "ID": pid})

print(f"Total unique products: {len(data)}")

# Get Shopify details
def get_access_token():
    payload = {
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(TOKEN_ENDPOINT, json=payload)
    response.raise_for_status()
    return response.json().get("access_token")

token = get_access_token()

def get_product_details(pid):
    query = """
    query getProduct($id: ID!) {
      product(id: $id) {
        handle
        vendor
        variants(first: 1) {
          edges {
            node {
              sku
            }
          }
        }
      }
    }
    """
    # GID format: gid://shopify/Product/123456789
    gid = f"gid://shopify/Product/{pid}"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token
    }
    resp = requests.post(GRAPHQL_ENDPOINT, json={"query": query, "variables": {"id": gid}}, headers=headers)
    if resp.status_code == 200:
        res_json = resp.json()
        if "errors" in res_json:
            print(f"Error for ID {pid}: {res_json['errors']}")
            return None
        p = res_json.get("data", {}).get("product")
        if p:
            sku = None
            if p["variants"]["edges"]:
                sku = p["variants"]["edges"][0]["node"]["sku"]
            return {
                "Handle": p["handle"],
                "SKU": sku,
                "Vendor": p["vendor"]
            }
    return None

final_data = []
for item in data:
    print(f"Fetching details for ID {item['ID']}...")
    details = get_product_details(item['ID'])
    if details:
        final_data.append(details)
    else:
        print(f"Could not find product with ID {item['ID']}")

df = pd.DataFrame(final_data)
os.makedirs("results", exist_ok=True)
output_path = "results/custom_scrape_list.csv"
df.to_csv(output_path, index=False)
print(f"Saved {len(final_data)} products to {output_path}")
