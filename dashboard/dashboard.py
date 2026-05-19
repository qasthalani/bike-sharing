import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

sns.set(style='dark')

# ── Colors ─────────────────────────────────────────────────────────────────────
BASE_COLOR      = "#4A90D9"   # blue  — base color for all bars
HIGHLIGHT_COLOR = "#E07B39"   # orange — highlights the bar with the highest value

def get_bar_colors(counts):
    """Return a color list: highlight for the highest value, base color for the rest."""
    max_val = max(counts) if counts else 0
    return [HIGHLIGHT_COLOR if v == max_val else BASE_COLOR for v in counts]

def add_bar_annotations(ax, counts, fontsize=18):
    """Add value labels above each bar."""
    for i, v in enumerate(counts):
        ax.text(
            i, v + max(counts) * 0.01,
            f"{int(v):,}",
            ha='center', va='bottom',
            fontsize=fontsize, fontweight='bold', color='white'
        )

# ── Data Preparation Helpers ───────────────────────────────────────────────────
def create_daily_orders_df(df):
    """Aggregate total rentals per day."""
    daily_orders_df = df.resample(rule='D', on='dteday').agg({
        'cnt': 'sum'
    }).reset_index()
    return daily_orders_df

def create_bycustomers_df(df):
    """Aggregate total casual vs registered customers."""
    bycustomers_df = df.groupby(by=["casual", "registered"]).agg({
        'cnt': 'sum'
    })
    bycustomers_df.rename(columns={"cnt": "total_customers"}, inplace=True)
    return bycustomers_df

def create_byday_df(df):
    """Aggregate rentals by weekday vs weekend."""
    byday_df = df.groupby(by=["is_workingday"]).agg({
        'casual': 'sum',
        'registered': 'sum',
        'cnt': 'sum'
    })
    return byday_df

def create_byseason_df(df):
    """Aggregate rentals by season."""
    byseason_df = df.groupby(by=["season_category"]).agg({
        'casual': 'sum',
        'registered': 'sum',
        'cnt': 'sum'
    })
    return byseason_df

def create_bytemp_df(df):
    """Aggregate rentals by temperature category."""
    by_temp = df.groupby(by=["temp_category"]).agg({
        'casual': 'sum',
        'registered': 'sum',
        'cnt': 'sum'
    })
    return by_temp

# Time segment constants
TIME_ORDER = ['Late Night', 'Morning Rush Hour', 'Midday', 'Evening Rush Hour', 'Night']
DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

def create_bytime_df(df):
    """Aggregate rentals by time-of-day segment (casual vs registered)."""
    return df.groupby('time_segment').agg({
        'casual':     'sum',
        'registered': 'sum',
        'cnt':        'sum'
    }).reindex(TIME_ORDER)

SEG_ORDER  = ['Champions', 'Loyal Days', 'Potential', 'Low Activity']
SEG_COLORS = ['#E07B39', '#4A90D9', '#7DB87D', '#B0B0B0']

def create_rfm_df(df):
    """
    Aggregate hourly data to daily, then compute R/F/M scores and segment labels.
    Returns the daily-level DataFrame with RFM columns.
    """
    daily = df.groupby('dteday').agg({
        'casual':          'sum',
        'registered':      'sum',
        'cnt':             'sum',
        'mnth':            'first',
        'yr':              'first',
        'is_workingday':   'first',
        'season_category': 'first',
    }).reset_index()

    if len(daily) < 3:
        daily['RFM_Segment'] = 'Potential'
        daily['magnitude']   = 'Medium'
        daily['RFM_Score']   = 5
        return daily

    # R — Recency
    max_date = daily['dteday'].max()
    daily['recency_days'] = (max_date - daily['dteday']).dt.days
    daily['R'] = pd.qcut(daily['recency_days'], q=3, labels=[3, 2, 1],
                          duplicates='drop').astype(int)

    # F — Frequency (monthly total)
    daily['monthly_total'] = daily.groupby(['yr', 'mnth'])['cnt'].transform('sum')
    daily['F'] = pd.qcut(daily['monthly_total'], q=3, labels=[1, 2, 3],
                          duplicates='drop').astype(int)

    # M — Magnitude (daily volume)
    p33, p66 = daily['cnt'].quantile(0.33), daily['cnt'].quantile(0.66)
    daily['magnitude'] = pd.cut(daily['cnt'],
                                 bins=[-float('inf'), p33, p66, float('inf')],
                                 labels=['Low', 'Medium', 'High'])
    daily['M'] = pd.cut(daily['cnt'],
                         bins=[-float('inf'), p33, p66, float('inf')],
                         labels=[1, 2, 3]).astype(int)

    # RFM Score + Segment
    daily['RFM_Score'] = daily['R'] + daily['F'] + daily['M']
    def seg(score):
        if score >= 8:   return 'Champions'
        elif score >= 6: return 'Loyal Days'
        elif score >= 4: return 'Potential'
        else:            return 'Low Activity'
    daily['RFM_Segment'] = daily['RFM_Score'].apply(seg)
    return daily

# ── Data Import & Preprocessing ────────────────────────────────────────────────
bike_df = pd.read_csv("C:\\Users\\slyth\\OneDrive\\Documents\\tugas stupen\\submission\\dashboard\\bike_sharing_clean.csv")

datetime_columns = ["dteday"]
bike_df.sort_values(by="dteday", inplace=True)
bike_df.reset_index(inplace=True)

for column in datetime_columns:
    bike_df[column] = pd.to_datetime(bike_df[column])

# ── Title ─────────────────────────────────────────────────────────────────────
st.title('Bike Sharing Dashboard 📊')

# ── Date Filter ────────────────────────────────────────────────────────────────
min_date = bike_df['dteday'].min()
max_date = bike_df['dteday'].max()

if "start_date" not in st.session_state:
    st.session_state.start_date = min_date

if "end_date" not in st.session_state:
    st.session_state.end_date = max_date

with st.sidebar:
    st.header("🔍 Filters")

    # ── Date Range ────────────────────────────────────────────────────────────
    st.subheader("📅 Date Range")
    st.caption("Click reset to restore all filters to their defaults.")

    try:
        date_input = st.date_input(
            label='Date Range',
            min_value=min_date,
            max_value=max_date,
            value=[st.session_state.start_date, st.session_state.end_date]
        )
        if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
            start_date, end_date = date_input
            st.session_state.start_date = start_date
            st.session_state.end_date   = end_date
        else:
            st.warning("⚠️ Please select a complete date range (start date & end date).")
            st.stop()
    except Exception as e:
        st.error(f"An error occurred with the date filter: {e}")
        st.stop()

    st.divider()

    # ── Year ──────────────────────────────────────────────────────────────────
    st.subheader("🗓️ Year")
    selected_year = st.selectbox(
        "Select year:",
        options=["All", "2011", "2012"],
        index=0
    )

    st.divider()

    # ── Season ────────────────────────────────────────────────────────────────
    st.subheader("⛅ Season")
    all_seasons = ["Spring", "Summer", "Fall", "Winter"]
    selected_seasons = st.multiselect(
        "Select season(s):",
        options=all_seasons,
        default=all_seasons
    )
    if not selected_seasons:
        st.warning("⚠️ Please select at least one season.")
        st.stop()

    st.divider()

    # ── Weather ───────────────────────────────────────────────────────────────
    st.subheader("🌤️ Weather Condition")
    all_weather = ["Clear", "Cloudy", "Rainy", "Stormy"]
    selected_weather = st.multiselect(
        "Select weather condition(s):",
        options=all_weather,
        default=all_weather
    )
    if not selected_weather:
        st.warning("⚠️ Please select at least one weather condition.")
        st.stop()

    st.divider()

    # ── Day Type ──────────────────────────────────────────────────────────────
    st.subheader("📆 Day Type")
    selected_day_type = st.radio(
        "Select day type:",
        options=["All", "Weekday", "Weekend"],
        index=0,
        horizontal=True
    )

    st.divider()

    # ── Reset All ─────────────────────────────────────────────────────────────
    if st.button("🔄 Reset All Filters", use_container_width=True):
        st.session_state.start_date = min_date
        st.session_state.end_date   = max_date
        st.rerun()

# ── Apply Filters ──────────────────────────────────────────────────────────────
WEATHER_CODE = {"Clear": 1, "Cloudy": 2, "Rainy": 3, "Stormy": 4}

main_df = bike_df[
    (bike_df["dteday"] >= pd.to_datetime(st.session_state.start_date)) &
    (bike_df["dteday"] <= pd.to_datetime(st.session_state.end_date))
].copy()

# Year filter
if selected_year != "All":
    yr_code = 0 if selected_year == "2011" else 1
    main_df = main_df[main_df["yr"] == yr_code]

# Season filter
if len(selected_seasons) < len(all_seasons):
    main_df = main_df[main_df["season_category"].isin(selected_seasons)]

# Weather filter
if len(selected_weather) < len(all_weather):
    codes = [WEATHER_CODE[w] for w in selected_weather]
    main_df = main_df[main_df["weathersit"].isin(codes)]

# Day type filter
if selected_day_type != "All":
    main_df = main_df[main_df["is_workingday"] == selected_day_type]

# Guard: empty result
if main_df.empty:
    st.warning("⚠️ No data matches the selected filters. Please adjust your filters.")
    st.stop()

st.caption(
    f"Showing **{len(main_df):,}** of **{len(bike_df):,}** records "
    f"based on current filters."
)

# ── Category order constants (used by dynamic label lists) ─────────────────────
SEASON_ORDER  = ['Spring', 'Summer', 'Fall', 'Winter']
TEMP_ORDER    = ['Very Cold', 'Cold', 'Mild', 'Warm', 'Hot']
DAY_ORDER     = ['Weekday', 'Weekend']

# ── Metrics with delta vs previous equivalent period ──────────────────────────
period_len = (
    pd.to_datetime(st.session_state.end_date) -
    pd.to_datetime(st.session_state.start_date)
).days + 1

prev_end   = pd.to_datetime(st.session_state.start_date) - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=period_len - 1)

prev_df = bike_df[
    (bike_df["dteday"] >= prev_start) &
    (bike_df["dteday"] <= prev_end)
]

total_rentals    = int(main_df["cnt"].sum())
total_casual     = int(main_df["casual"].sum())
total_registered = int(main_df["registered"].sum())

delta_rentals    = int(total_rentals    - prev_df["cnt"].sum())
delta_casual     = int(total_casual     - prev_df["casual"].sum())
delta_registered = int(total_registered - prev_df["registered"].sum())

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Rentals",          f"{total_rentals:,}",    delta=f"{delta_rentals:+,}")
with col2:
    st.metric("Total Casual Users",     f"{total_casual:,}",     delta=f"{delta_casual:+,}")
with col3:
    st.metric("Total Registered Users", f"{total_registered:,}", delta=f"{delta_registered:+,}")

st.caption("↑↓ Delta compared to the equivalent previous period of the same length.")

daily_orders_df = create_daily_orders_df(main_df)
bycustomers_df  = create_bycustomers_df(main_df)
byday_df        = create_byday_df(main_df)
byseason_df     = create_byseason_df(main_df)
bytemp_df       = create_bytemp_df(main_df)

# ── 1. Rental Trend Over Time ──────────────────────────────────────────────────
st.header("Monthly Performance 📈")

fig, ax = plt.subplots(figsize=(16, 8))
ax.plot(
    daily_orders_df["dteday"],
    daily_orders_df["cnt"],
    marker='o',
    linewidth=2,
    color=BASE_COLOR
)
ax.tick_params(axis='y', labelsize=20)
ax.tick_params(axis='x', labelsize=15)
st.pyplot(fig)
st.caption("💡 Rentals grew significantly from 2011 to 2012, with a clear seasonal peak each year in mid-to-late year.")

# ── 2. Customer Segmentation ───────────────────────────────────────────────────
st.header("Customer Segmentation 👥")

labels_pl = ['Casual', 'Registered']
counts_pl = [main_df['casual'].sum(), main_df['registered'].sum()]
colors_pl = get_bar_colors(counts_pl)

fig1, ax1 = plt.subplots(figsize=(20, 10))
sns.barplot(x=labels_pl, y=counts_pl, palette=colors_pl, ax=ax1)
add_bar_annotations(ax1, counts_pl, fontsize=22)

ax1.set_title('Total Users: Casual vs Registered', loc='center', fontsize=30)
ax1.set_xlabel(None)
ax1.set_ylabel('Total Rentals')
ax1.tick_params(axis='y', labelsize=20)
ax1.tick_params(axis='x', labelsize=25)

st.pyplot(fig1)
st.caption("💡 Registered users dominate — indicating high user loyalty and repeat usage.")

# ── 3. Rentals by Day Type ─────────────────────────────────────────────────────
st.header("Total Rentals by Day 📆")

labels_d = [d for d in DAY_ORDER if d in main_df['is_workingday'].unique()]
counts_d = [main_df[main_df['is_workingday'] == d]['cnt'].sum() for d in labels_d]
colors_d = get_bar_colors(counts_d)

fig2, ax2 = plt.subplots(figsize=(20, 10))
sns.barplot(x=labels_d, y=counts_d, palette=colors_d, ax=ax2)
add_bar_annotations(ax2, counts_d, fontsize=22)

ax2.set_title('Total Rentals: Weekday vs Weekend', loc='center', fontsize=30)
ax2.set_xlabel(None)
ax2.set_ylabel('Total Rentals')
ax2.tick_params(axis='y', labelsize=20)
ax2.tick_params(axis='x', labelsize=25)

st.pyplot(fig2)
st.caption("💡 Rentals are higher on weekdays, driven by registered users commuting daily.")

# ── 4. Rentals by Season ───────────────────────────────────────────────────────
st.header("Total Rentals by Season ⛅")

labels_ss = [s for s in SEASON_ORDER if s in main_df['season_category'].unique()]
counts_ss = [main_df[main_df['season_category'] == s]['cnt'].sum() for s in labels_ss]
colors_ss = get_bar_colors(counts_ss)

fig3, ax3 = plt.subplots(figsize=(20, 10))
sns.barplot(x=labels_ss, y=counts_ss, palette=colors_ss, ax=ax3)
add_bar_annotations(ax3, counts_ss, fontsize=22)

ax3.set_title('Total Rentals by Season', loc='center', fontsize=30)
ax3.set_xlabel(None)
ax3.set_ylabel('Total Rentals')
ax3.tick_params(axis='y', labelsize=20)
ax3.tick_params(axis='x', labelsize=25)

st.pyplot(fig3)
st.caption("💡 Fall records the highest rentals; Spring is the quietest season.")

# ── 5. Rentals by Weather & Temperature ───────────────────────────────────────
st.header("Total Rentals by Weather & Temperature ☀️")

# Dynamic labels — only show categories present in filtered data
labels_w = [w for w in WEATHER_CODE if WEATHER_CODE[w] in main_df['weathersit'].unique()]
counts_w = [main_df[main_df['weathersit'] == WEATHER_CODE[w]]['cnt'].sum() for w in labels_w]
colors_w = get_bar_colors(counts_w)

labels_t = [t for t in TEMP_ORDER if t in main_df['temp_category'].unique()]
counts_t = [main_df[main_df['temp_category'] == t]['cnt'].sum() for t in labels_t]
colors_t = get_bar_colors(counts_t)

fig4, ax4 = plt.subplots(nrows=1, ncols=2, figsize=(35, 10))

sns.barplot(x=labels_w, y=counts_w, palette=colors_w, ax=ax4[0])
add_bar_annotations(ax4[0], counts_w, fontsize=28)
ax4[0].set_title("Total Rentals by Weather Condition", loc="center", fontsize=50)
ax4[0].set_xlabel(None)
ax4[0].set_ylabel('Total Rentals', fontsize=30)
ax4[0].tick_params(axis='x', labelsize=30)
ax4[0].tick_params(axis='y', labelsize=30)

sns.barplot(x=labels_t, y=counts_t, palette=colors_t, ax=ax4[1])
add_bar_annotations(ax4[1], counts_t, fontsize=28)
ax4[1].set_title("Total Rentals by Temperature", loc="center", fontsize=50)
ax4[1].set_xlabel(None)
ax4[1].set_ylabel('Total Rentals', fontsize=30)
ax4[1].tick_params('x', labelsize=30)
ax4[1].tick_params('y', labelsize=30)

plt.tight_layout()
st.pyplot(fig4)
st.caption("💡 Clear weather and mild-to-warm temperatures drive the highest rental activity.")


# ── 6. Peak Hour Analysis ──────────────────────────────────────────────────────
st.header("Peak Hour Analysis 🕐")

bytime_df = create_bytime_df(main_df)

# Chart A — Grouped bar: casual vs registered per time segment
seg_casual     = bytime_df['casual'].tolist()
seg_registered = bytime_df['registered'].tolist()
x_pos = range(len(TIME_ORDER))
width = 0.35

fig5, ax5 = plt.subplots(figsize=(16, 7))
bars_c = ax5.bar([i - width/2 for i in x_pos], seg_casual,     width,
                 label='Casual', color=BASE_COLOR, alpha=0.90)
bars_r = ax5.bar([i + width/2 for i in x_pos], seg_registered, width,
                 label='Registered', color=HIGHLIGHT_COLOR, alpha=0.90)

for bar in bars_c:
    ax5.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + max(seg_casual + seg_registered) * 0.005,
             f"{int(bar.get_height()):,}",
             ha="center", va="bottom", fontsize=11, fontweight="bold")
for bar in bars_r:
    ax5.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + max(seg_casual + seg_registered) * 0.005,
             f"{int(bar.get_height()):,}",
             ha="center", va="bottom", fontsize=11, fontweight="bold")

ax5.set_title("Casual vs Registered Rentals by Time Segment", fontsize=22)
ax5.set_xlabel(None)
ax5.set_ylabel("Total Rentals", fontsize=16)
ax5.set_xticks(list(x_pos))
ax5.set_xticklabels(TIME_ORDER, fontsize=14)
ax5.tick_params(axis="y", labelsize=14)
ax5.legend(fontsize=14)
plt.tight_layout()
st.pyplot(fig5)
st.caption("💡 Registered users dominate rush hours — a clear commuter signal. "
           "Casual users are more active during Midday, reflecting leisure usage.")

# Chart B — Heatmap: average rentals per hour x day of week
pivot_heatmap = main_df.pivot_table(
    values="cnt", index="hr", columns="weekday", aggfunc="mean"
).rename(columns=dict(enumerate(DAY_LABELS)))

fig6, ax6 = plt.subplots(figsize=(14, 9))
sns.heatmap(
    pivot_heatmap,
    cmap="YlOrRd",
    linewidths=0.4,
    annot=True, fmt=".0f", annot_kws={"size": 9},
    ax=ax6
)
ax6.set_title("Average Hourly Rentals — Hour vs Day of Week", fontsize=20)
ax6.set_xlabel("Day of Week", fontsize=14)
ax6.set_ylabel("Hour of Day", fontsize=14)
ax6.invert_yaxis()
plt.tight_layout()
st.pyplot(fig6)
st.caption("💡 Weekdays show a bimodal pattern (08:00 & 17:00-18:00). "
           "Weekends peak broadly around 11:00-15:00.")

# Chart C — Line chart: avg rentals per hour (weekday vs weekend)
avg_hour     = main_df.groupby(["hr", "is_workingday"])["cnt"].mean().reset_index()
weekday_line = avg_hour[avg_hour["is_workingday"] == "Weekday"]
weekend_line = avg_hour[avg_hour["is_workingday"] == "Weekend"]

fig7, ax7 = plt.subplots(figsize=(14, 6))
ax7.plot(weekday_line["hr"], weekday_line["cnt"],
         marker="o", linewidth=2.5, color=HIGHLIGHT_COLOR, label="Weekday")
ax7.plot(weekend_line["hr"], weekend_line["cnt"],
         marker="o", linewidth=2.5, color=BASE_COLOR, label="Weekend")

ax7.axvspan(6,  9,  alpha=0.08, color=HIGHLIGHT_COLOR)
ax7.axvspan(16, 19, alpha=0.08, color=HIGHLIGHT_COLOR)

ax7.set_title("Average Rentals per Hour: Weekday vs Weekend", fontsize=20)
ax7.set_xlabel("Hour of Day", fontsize=14)
ax7.set_ylabel("Average Rentals", fontsize=14)
ax7.set_xticks(range(0, 24))
ax7.tick_params(axis="both", labelsize=12)
ax7.legend(fontsize=13)
ax7.grid(axis="y", linestyle="--", alpha=0.4)
plt.tight_layout()
st.pyplot(fig7)
st.caption("💡 The shaded bands highlight morning and evening rush hours. "
           "Fleet availability should be maximized during these windows on weekdays.")

# ── 7. Temporal RFM Segmentation ───────────────────────────────────────────────
st.header("Rental Volume Segmentation — Temporal RFM 📊")

rfm_df = create_rfm_df(main_df)

# ── Segment summary metrics ────────────────────────────────────────────────────
seg_counts = rfm_df['RFM_Segment'].value_counts()

m1, m2, m3, m4 = st.columns(4)
m1.metric("🏆 Champions",    f"{seg_counts.get('Champions',    0)} days")
m2.metric("💙 Loyal Days",   f"{seg_counts.get('Loyal Days',   0)} days")
m3.metric("🌱 Potential",    f"{seg_counts.get('Potential',    0)} days")
m4.metric("⚪ Low Activity", f"{seg_counts.get('Low Activity', 0)} days")

# ── Chart A: Days per segment ──────────────────────────────────────────────────
seg_bar = rfm_df['RFM_Segment'].value_counts().reindex(SEG_ORDER).fillna(0)

fig_r1, ax_r1 = plt.subplots(figsize=(12, 5))
bars = ax_r1.bar(SEG_ORDER, seg_bar.values, color=SEG_COLORS,
                  edgecolor='white', linewidth=1.2)
for bar, val in zip(bars, seg_bar.values):
    ax_r1.text(bar.get_x() + bar.get_width() / 2,
               bar.get_height() + seg_bar.max() * 0.01,
               f"{int(val)} days", ha="center", va="bottom", fontsize=14, fontweight="bold")

ax_r1.set_title("Number of Days by RFM Segment", fontsize=20)
ax_r1.set_xlabel(None)
ax_r1.set_ylabel("Number of Days", fontsize=14)
ax_r1.tick_params(axis="x", labelsize=14)
ax_r1.tick_params(axis="y", labelsize=12)
plt.tight_layout()
st.pyplot(fig_r1)
st.caption("💡 Champion and Loyal Days dominate the dataset — concentrated in mid-year peak months.")

# ── Chart B: Avg rentals per segment (casual vs registered heatmap) ────────────
seg_stats = rfm_df.groupby("RFM_Segment").agg(
    Avg_Total=("cnt", "mean"),
    Avg_Casual=("casual", "mean"),
    Avg_Registered=("registered", "mean")
).reindex(SEG_ORDER).round(0).astype(int)

heatmap_data = seg_stats.T
heatmap_norm = heatmap_data.div(heatmap_data.max(axis=1), axis=0)

fig_r2, ax_r2 = plt.subplots(figsize=(12, 4))
sns.heatmap(
    heatmap_norm,
    annot=heatmap_data.values, fmt="g", annot_kws={"size": 15},
    cmap="YlOrRd", linewidths=0.5,
    xticklabels=SEG_ORDER,
    yticklabels=["Total", "Casual", "Registered"],
    ax=ax_r2, cbar=False
)
ax_r2.set_title("Average Daily Rentals by RFM Segment", fontsize=18)
ax_r2.set_xlabel(None)
ax_r2.tick_params(axis="x", labelsize=13)
ax_r2.tick_params(axis="y", labelsize=13)
plt.tight_layout()
st.pyplot(fig_r2)
st.caption("💡 Registered users show a steeper gap across segments — they are the primary driver of Champion-day performance.")

# ── Chart C: Segment distribution by month (stacked bar) ──────────────────────
month_seg = rfm_df.groupby(["mnth", "RFM_Segment"]).size().unstack(fill_value=0)
month_seg = month_seg.reindex(columns=SEG_ORDER, fill_value=0)
month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]
month_labels_filtered = [month_labels[m-1] for m in month_seg.index]

fig_r3, ax_r3 = plt.subplots(figsize=(14, 6))
bottom = [0] * len(month_seg)
for seg, color in zip(SEG_ORDER, SEG_COLORS):
    if seg in month_seg.columns:
        vals = month_seg[seg].values
        ax_r3.bar(range(len(month_seg)), vals, bottom=bottom,
                  label=seg, color=color, edgecolor="white", linewidth=0.8)
        bottom = [b + v for b, v in zip(bottom, vals)]

ax_r3.set_title("RFM Segment Distribution by Month", fontsize=20)
ax_r3.set_xlabel("Month", fontsize=14)
ax_r3.set_ylabel("Number of Days", fontsize=14)
ax_r3.set_xticks(range(len(month_seg)))
ax_r3.set_xticklabels(month_labels_filtered, fontsize=12)
ax_r3.legend(loc="upper left", fontsize=12)
ax_r3.grid(axis="y", linestyle="--", alpha=0.4)
ax_r3.tick_params(axis="y", labelsize=12)
plt.tight_layout()
st.pyplot(fig_r3)
st.caption("💡 Champions and Loyal Days peak in Aug–Oct. Jan–Feb are dominated by Low Activity days — "
           "prime targets for off-season promotions.")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style='color: #9CA3AF; font-size: 14px;'>
        <p>Data Source: 
            <a href='https://www.kaggle.com/datasets/lakshmi25npathi/bike-sharing-dataset' target='_blank'>
            Bike Sharing Dataset — Kaggle
            </a>
        </p>
        <p>Created by: <b>Nabilah Yasmin Qasthalani</b> © 2026</p>
    </div>
    """,
    unsafe_allow_html=True
)
