import gradio as gr
import pandas as pd
import requests
from supabase import create_client

# --- 1. CONFIGURATION & ASSETS ---
SUPABASE_URL = "https://qhotebqodnirjmazkwik.supabase.co"
SUPABASE_KEY = "sb_publishable_gDNkljExtJ6zRxEj9FK4QQ_pDkjRq3d"
LOGO_URL = "https://github.com/NayanRAwasthi/Mishtee-Magic/blob/main/logo%20mishtee%20magic.jpg?raw=true"
STYLE_URL = "https://raw.githubusercontent.com/NayanRAwasthi/Mishtee-Magic/refs/heads/main/Style.py"

# Initialize Supabase Client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch Custom CSS from GitHub
try:
    mishtee_css = requests.get(STYLE_URL).text
except:
    # Fallback minimal CSS if URL is unreachable
    mishtee_css = ".gradio-container {background-color: #FAF9F6; font-family: 'serif';}"

# --- 2. BACKEND FUNCTIONS ---

def get_customer_orders(phone_number):
    """Retrieves customer greeting and historical order data."""
    if not phone_number or len(phone_number) < 10:
        return "Please enter a valid 10-digit mobile number.", pd.DataFrame()

    # Fetch Customer Name
    cust_res = supabase.table("customers").select("full_name").eq("phone", phone_number).maybe_single().execute()

    if not cust_res.data:
        return "Namaste! It looks like you're new to the magic. Shall we create an account?", pd.DataFrame()

    greeting = f"## Namaste, {cust_res.data['full_name']} ji! \nGreat to see you again."

    # Fetch Orders with Product Details
    order_res = supabase.table("orders").select(
        "order_id, order_date, qty_kg, order_value_inr, status, products(sweet_name)"
    ).eq("cust_phone", phone_number).execute()

    if not order_res.data:
        return greeting, pd.DataFrame(columns=["Order ID", "Date", "Product", "Qty (kg)", "Value (₹)", "Status"])

    flat_orders = [{
        "Order ID": r['order_id'],
        "Date": r['order_date'],
        "Product": r['products']['sweet_name'],
        "Qty (kg)": r['qty_kg'],
        "Value (₹)": r['order_value_inr'],
        "Status": r['status']
    } for r in order_res.data]

    return greeting, pd.DataFrame(flat_orders)

def get_trending_products():
    """Aggregates top 4 best-selling products."""
    res = supabase.table("orders").select("product_id, qty_kg, products(sweet_name, variant_type)").execute()

    if not res.data:
        return pd.DataFrame(columns=["Rank", "Sweet Name", "Variant", "Total Sold (kg)"])

    df = pd.DataFrame([{
        "name": r['products']['sweet_name'],
        "variant": r['products']['variant_type'],
        "qty": float(r['qty_kg'])
    } for r in res.data])

    trending = df.groupby(['name', 'variant'])['qty'].sum().reset_index()
    trending = trending.sort_values(by='qty', ascending=False).head(4)
    trending.insert(0, 'Rank', range(1, len(trending) + 1))
    trending.columns = ["Rank", "Sweet Name", "Variant", "Total Sold (kg)"]
    return trending

# --- 3. GRADIO UI LAYOUT ---

with gr.Blocks(css=mishtee_css, title="MishTee-Magic") as demo:

    # Header Section
    with gr.Column(elem_id="header-container"):
        gr.Image(LOGO_URL, show_label=False, container=False, width=220, interactive=False)
        gr.Markdown("<center><h3>Heritage in Every Bite • Purity & Health First</h3></center>")

    gr.HTML("<div style='height: 20px;'></div>") # Replaced gr.Space() with gr.HTML for compatibility

    # Login Logic Row
    with gr.Row():
        with gr.Column(scale=2):
            phone_input = gr.Textbox(label="Enter Mobile Number", placeholder="98XXXXXXXX", max_lines=1)
            login_btn = gr.Button("REVEAL THE MAGIC", variant="primary")

    # Dynamic Greeting Area
    greeting_display = gr.Markdown("Enter your details to view your artisanal collection.")

    gr.HTML("<hr style='border: 0.5px solid #C06C5C; opacity: 0.3; margin: 30px 0;'>")

    # Data Display (Tabbed View)
    with gr.Tabs():
        with gr.TabItem("My Order History"):
            history_table = gr.Dataframe(interactive=False)

        with gr.TabItem("Trending Today"):
            trending_table = gr.Dataframe(interactive=False)

    # --- 4. APP EVENT TRIGGERS ---

    def login_sequence(phone):
        greeting, history_df = get_customer_orders(phone)
        trending_df = get_trending_products()
        return greeting, history_df, trending_df

    login_btn.click(
        fn=login_sequence,
        inputs=phone_input,
        outputs=[greeting_display, history_table, trending_table]
    )

    # Footer
    gr.Markdown("<center><small>MishTee-Magic | Minimalist Artisanal D2C Concept</small></center>")

if __name__ == "__main__":
    demo.launch()
