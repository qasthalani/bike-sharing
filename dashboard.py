import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from babel.numbers import format_currency
sns.set(style='dark')

# mempersiapkan data
def create_daily_orders_df(df):
    daily_orders_df = df.resample(rule='D', on='dteday').agg({
        'cnt': 'sum'
    }).reset_index()

    return daily_orders_df

def create_bycustomers_df(df):
    bycustomers_df = df.groupby(by=["casual", "registered"]).agg({
        'cnt':'sum'
    })
    bycustomers_df.rename(columns={
        "cnt": "total_customers"
    }, inplace=True)

    return bycustomers_df

def create_byday_df(df):
    byday_df = df.groupby(by=["is_workingday"]).agg({
        'casual': 'sum',
        'registered': 'sum',
        'cnt': 'sum'
    })

    return byday_df

def create_byseason_df(df):
    byseason_df = df.groupby(by=["season_category"]).agg({
        'casual': 'sum',
        'registered': 'sum',
        'cnt': 'sum'
    })

    return byseason_df

def create_bytemp_df(df):
    by_temp = df.groupby(by=["temp_category"]).agg({
        'casual': 'sum',
        'registered': 'sum',
        'cnt': 'sum'
    })

    return by_temp

#melakukan import data
bike_df = pd.read_csv("bike_sharing_cleaned.csv")

datetime_columns = ["dteday"]
bike_df.sort_values(by="dteday", inplace=True)
bike_df.reset_index(inplace=True)

for column in datetime_columns:
    bike_df[column] = pd.to_datetime(bike_df[column])

# membuat judul
st.title('Bike Sharing Dashboard 📊')

col1, col2, col3 = st.columns(3)

with col1:
    total_rentals = bike_df.cnt.sum()
    st.metric("Total Rentals", value=total_rentals)

with col2:
    total_casual = bike_df.casual.sum()
    st.metric("Total Casual Customers", value=total_casual)

with col3:
    total_registered = bike_df.registered.sum()
    st.metric("Total Registered Customers", value=total_registered)

# membuat filter untuk performa
min_date = bike_df['dteday'].min()
max_date = bike_df['dteday'].max()

if "start_date" not in st.session_state:
    st.session_state.start_date = min_date

if "end_date" not in st.session_state:
    st.session_state.end_date = max_date

# membuat sidebar
with st.sidebar:
    st.caption("Klik reset untuk kembali ke rentang awal")
    start_date, end_date = st.date_input(
        label='Rentang Waktu',
        min_value=min_date,
        max_value=max_date,
        value=[st.session_state.start_date, st.session_state.end_date]
    )

    # update session state
    st.session_state.start_date = start_date
    st.session_state.end_date = end_date

    # tombol reset
    if st.button("Reset Filter"):
        st.session_state.start_date = min_date
        st.session_state.end_date = max_date
        st.rerun()

main_df = bike_df[
    (bike_df["dteday"] >= pd.to_datetime(st.session_state.start_date)) &
    (bike_df["dteday"] <= pd.to_datetime(st.session_state.end_date))
]

daily_orders_df = create_daily_orders_df(main_df)
bycustomers_df = create_bycustomers_df(main_df)
byday_df = create_byday_df(main_df)
byseason_df = create_byseason_df(main_df)
bytemp_df = create_bytemp_df(main_df)

# visualisasi tren penyewaan sepeda dari waktu ke waktu
st.header("Monthly Performance 📈")

fig, ax = plt.subplots(figsize=(16, 8))
ax.plot(
daily_orders_df["dteday"],
daily_orders_df["cnt"],
    marker='o', 
    linewidth=2,
    color="#90CAF9"
    )
ax.tick_params(axis='y', labelsize=20)
ax.tick_params(axis='x', labelsize=15)

st.pyplot(fig)

# membuat visualisasi pelanggan
st.header("Customers Segmentation 👥")

labels_pl = ['Casual', 'Registered']
counts_pl = [main_df['casual'].sum(), main_df['registered'].sum()]

fig1, ax1 = plt.subplots(figsize=(20, 10))
sns.barplot(x=labels_pl, 
            y=counts_pl, 
            palette='coolwarm', 
            ax=ax1)

ax1.set_title('Total Customers (Casual vs Registered)', loc='center', fontsize=30)
ax1.set_xlabel(None)
ax1.set_ylabel(None)
ax1.tick_params(axis='y', labelsize=20)
ax1.tick_params(axis='x', labelsize=15)

st.pyplot(fig1)

# membuat visualisasi jumlah penyewaan berdasarkan hari
st.header("Total Rental by Day 📆")

labels_d = ['Hari Kerja', 'Akhir Pekan']
counts_d = [main_df[main_df['is_workingday'] == 'Hari Kerja']['cnt'].sum(), 
             main_df[main_df['is_workingday'] == 'Akhir Pekan']['cnt'].sum()]

fig2, ax2 = plt.subplots(figsize=(20, 10))
sns.barplot(x=labels_d,
            y=counts_d,
            palette='coolwarm',
            ax=ax2)

ax2.set_xlabel(None)
ax2.set_ylabel(None)
ax2.tick_params(axis='y', labelsize=20)
ax2.tick_params(axis='x', labelsize=15)

st.pyplot(fig2)

# membuat visualisasi jumlah penyewaan berdasarkan musim
st.header("Total Rental by Season ⛅")

labels_ss = ['Musim Semi', 'Musim Panas', 'Musim Gugur', 'Musim Dingin']
counts_ss = [main_df[main_df['season_category'] == 'Musim Semi']['cnt'].sum(),
             main_df[main_df['season_category'] == 'Musim Panas']['cnt'].sum(),
             main_df[main_df['season_category'] == 'Musim Gugur']['cnt'].sum(),
             main_df[main_df['season_category'] == 'Musim Dingin']['cnt'].sum()]

fig3, ax3 = plt.subplots(figsize=(20, 10))
sns.barplot(x=labels_ss,
            y=counts_ss,
            palette='coolwarm',
            ax=ax3)

ax3.set_xlabel(None)
ax3.set_ylabel(None)
ax3.tick_params(axis='y', labelsize=20)
ax3.tick_params(axis='x', labelsize=15)

st.pyplot(fig3)

st.header("Total Rental by Weather & Temp ☀️")

labels_w = ['Cuaca Cerah', 'Cuaca Berawan', 'Cuaca Hujan', 'Cuaca Badai']
counts_w = [main_df[main_df['weathersit'] == 1]['cnt'].sum(),
            main_df[main_df['weathersit'] == 2]['cnt'].sum(),
            main_df[main_df['weathersit'] == 3]['cnt'].sum(),
            main_df[main_df['weathersit'] == 4]['cnt'].sum()]

fig4, ax4 = plt.subplots(nrows=1, ncols=2, figsize=(35, 10))

sns.barplot(x=labels_w,
            y=counts_w,
            palette='coolwarm',
            ax=ax4[0])

ax4[0].set_title("Total Rental by Weather", loc="center", fontsize=50)
ax4[0].set_xlabel(None)
ax4[0].set_ylabel(None)
ax4[0].tick_params(axis='x', labelsize=30)
ax4[0].tick_params(axis='y', labelsize=30)

labels_t = ['Very Cold', 'Cold', 'Mild', 'Warm', 'Hot']
counts_t = [main_df[main_df['temp_category'] == 'Very Cold']['cnt'].sum(),
            main_df[main_df['temp_category'] == 'Cold']['cnt'].sum(),
            main_df[main_df['temp_category'] == 'Mild']['cnt'].sum(),
            main_df[main_df['temp_category'] == 'Warm']['cnt'].sum(),
            main_df[main_df['temp_category'] == 'Hot']['cnt'].sum()]

sns.barplot(x=labels_t,
            y=counts_t,
            palette='coolwarm',
            ax=ax4[1])

ax4[1].set_title("Total Rental by Temp", loc="center", fontsize=50)
ax4[1].set_xlabel(None)
ax4[1].set_ylabel(None)
ax4[1].tick_params('x', labelsize=30)
ax4[1].tick_params('y', labelsize=30)

plt.tight_layout()
st.pyplot(fig4)

st.markdown("---")

st.markdown(
    """
    <div style='color: #9CA3AF; font-size: 14px;'>
        <p>Sumber Data: 
            <a href='https://www.kaggle.com/datasets/lakshmi25npathi/bike-sharing-dataset' target='_blank'>
            Bike Sharing Dataset
            </a>
        </p>
        <p>Dibuat oleh: <b>Nabilah Yasmin Qasthalani</b> © 2026</p>
    </div>
    """,
    unsafe_allow_html=True
)
