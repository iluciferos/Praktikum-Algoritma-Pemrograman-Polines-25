# main_app.py
import streamlit as st
import datetime
import pandas as pd
import locale

# ── Setup locale untuk format Rupiah ─────────────────────────────────
try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Indonesian_Indonesia.1252')
    except Exception:
        pass  # Locale tidak tersedia, pakai format manual

def format_rp(angka):
    try:
        return locale.currency(angka or 0, grouping=True, symbol='Rp ')[:-3]
    except Exception:
        return f"Rp {angka or 0:,.0f}".replace(",", ".")

# ── Import modul aplikasi ─────────────────────────────────────────────
try:
    from model import Transaksi
    from manajer_anggaran import AnggaranHarian
    from konfigurasi import KATEGORI_PENGELUARAN
except ImportError as e:
    st.error(f"Gagal mengimpor modul: {e}. Pastikan semua file .py ada di satu folder.")
    st.stop()

# ── Konfigurasi halaman ───────────────────────────────────────────────
st.set_page_config(
    page_title="Catatan Pengeluaran",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Inisialisasi AnggaranHarian (cache agar tidak buat ulang) ─────────
@st.cache_resource
def get_anggaran_manager():
    print(">>> STREAMLIT: Menginisialisasi AnggaranHarian...")
    return AnggaranHarian()

anggaran = get_anggaran_manager()


# ═══════════════════════════════════════════════════════════════════════
# HALAMAN 1: TAMBAH PENGELUARAN
# ═══════════════════════════════════════════════════════════════════════
def halaman_input(anggaran: AnggaranHarian):
    st.header("💸 Tambah Pengeluaran Baru")

    with st.form("form_transaksi_baru", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            deskripsi = st.text_input("Deskripsi*", placeholder="Contoh: Makan siang")
        with col2:
            kategori = st.selectbox("Kategori*:", KATEGORI_PENGELUARAN, index=0)

        col3, col4 = st.columns([1, 1])
        with col3:
            jumlah = st.number_input(
                "Jumlah (Rp)*:", min_value=0.01, step=1000.0,
                format="%.0f", value=None, placeholder="Contoh: 25000"
            )
        with col4:
            tanggal = st.date_input("Tanggal*:", value=datetime.date.today())

        submitted = st.form_submit_button("💾 Simpan Transaksi")

        if submitted:
            if not deskripsi:
                st.warning("Deskripsi wajib diisi!", icon="⚠️")
            elif jumlah is None or jumlah <= 0:
                st.warning("Jumlah wajib diisi dan harus positif!", icon="⚠️")
            else:
                with st.spinner("Menyimpan..."):
                    tx = Transaksi(deskripsi, float(jumlah), kategori, tanggal)
                    if anggaran.tambah_transaksi(tx):
                        st.success(f"Transaksi '{deskripsi}' berhasil disimpan!", icon="✅")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Gagal menyimpan transaksi.", icon="❌")


# ═══════════════════════════════════════════════════════════════════════
# HALAMAN 2: RIWAYAT + HAPUS TRANSAKSI (TUGAS)
# ═══════════════════════════════════════════════════════════════════════
def halaman_riwayat(anggaran: AnggaranHarian):
    st.subheader("📋 Riwayat Semua Transaksi")

    if st.button("🔄 Refresh Riwayat"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Memuat riwayat..."):
        df_transaksi = anggaran.get_dataframe_transaksi()

    if df_transaksi is None:
        st.error("Gagal mengambil data riwayat.")
        return
    elif df_transaksi.empty:
        st.info("Belum ada transaksi. Tambahkan lewat menu 'Tambah'.")
        return

    # Tampilkan tabel riwayat
    st.dataframe(df_transaksi, use_container_width=True, hide_index=True)
    st.caption(f"Total {len(df_transaksi)} transaksi ditemukan.")

    # ── Fitur Hapus Transaksi ─────────────────────────────────────────
    st.divider()
    st.subheader("🗑️ Hapus Transaksi")
    st.info("Masukkan ID transaksi yang ingin dihapus (lihat kolom 'id' pada tabel di atas).")

    col_input, col_btn = st.columns([2, 1])
    with col_input:
        id_hapus = st.number_input(
            "ID Transaksi yang akan dihapus:",
            min_value=1, step=1, value=None,
            placeholder="Masukkan ID...",
            key="input_id_hapus"
        )

    with col_btn:
        # Tombol utama untuk meminta konfirmasi
        st.write("")  # spacer agar sejajar
        tombol_hapus = st.button("🗑️ Hapus Transaksi", type="primary", key="btn_hapus")

    # Simpan state konfirmasi di session_state
    if tombol_hapus:
        if id_hapus is None:
            st.warning("Masukkan ID transaksi terlebih dahulu!", icon="⚠️")
        else:
            # Cek apakah ID ada di tabel
            id_list = df_transaksi['id'].tolist()
            if int(id_hapus) not in id_list:
                st.error(f"ID {int(id_hapus)} tidak ditemukan dalam tabel!", icon="❌")
            else:
                # Simpan ID yang akan dihapus dan tampilkan konfirmasi
                st.session_state['id_akan_dihapus'] = int(id_hapus)

    # Tampilkan kotak konfirmasi jika ada ID yang menunggu konfirmasi
    if 'id_akan_dihapus' in st.session_state:
        id_konfirmasi = st.session_state['id_akan_dihapus']

        # Cari detail transaksi yang akan dihapus
        baris = df_transaksi[df_transaksi['id'] == id_konfirmasi]
        if not baris.empty:
            detail = baris.iloc[0]
            st.warning(
                f"⚠️ Anda yakin ingin menghapus transaksi berikut?\n\n"
                f"**ID:** {detail['id']}  |  "
                f"**Tanggal:** {detail['tanggal']}  |  "
                f"**Deskripsi:** {detail['deskripsi']}  |  "
                f"**Jumlah:** {detail['Jumlah (Rp)']}",
                icon="⚠️"
            )

        col_ya, col_tidak = st.columns([1, 1])
        with col_ya:
            if st.button("✅ Ya, Hapus!", type="primary", key="btn_konfirmasi_ya"):
                with st.spinner("Menghapus..."):
                    berhasil = anggaran.hapus_transaksi(id_konfirmasi)
                if berhasil:
                    st.success(f"Transaksi ID {id_konfirmasi} berhasil dihapus!", icon="✅")
                    del st.session_state['id_akan_dihapus']
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Gagal menghapus transaksi.", icon="❌")

        with col_tidak:
            if st.button("❌ Batal", key="btn_konfirmasi_tidak"):
                del st.session_state['id_akan_dihapus']
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# HALAMAN 3: RINGKASAN
# ═══════════════════════════════════════════════════════════════════════
def halaman_ringkasan(anggaran: AnggaranHarian):
    st.subheader("📊 Ringkasan Pengeluaran")

    col_filter1, col_filter2 = st.columns([1, 2])

    with col_filter1:
        pilihan_periode = st.selectbox(
            "Filter Periode:",
            ["Semua Waktu", "Hari Ini", "Pilih Tanggal Tertentu"],
            key="filter_periode"
        )

    tanggal_filter = None
    label_periode  = "(Semua Waktu)"

    if pilihan_periode == "Hari Ini":
        tanggal_filter = datetime.date.today()
        label_periode  = f"({tanggal_filter.strftime('%d %b %Y')})"
    elif pilihan_periode == "Pilih Tanggal Tertentu":
        if 'tanggal_pilihan_state' not in st.session_state:
            st.session_state.tanggal_pilihan_state = datetime.date.today()
        with col_filter1:
            tanggal_filter = st.date_input(
                "Pilih Tanggal:",
                value=st.session_state.tanggal_pilihan_state,
                key="tanggal_pilihan"
            )
        label_periode = f"({tanggal_filter.strftime('%d %b %Y')})"

    with col_filter2:
        @st.cache_data(ttl=300)
        def hitung_total_cached(tgl):
            return anggaran.hitung_total_pengeluaran(tanggal=tgl)

        total = hitung_total_cached(tanggal_filter)
        st.metric(label=f"Total Pengeluaran {label_periode}", value=format_rp(total))

    st.divider()
    st.subheader(f"Pengeluaran per Kategori {label_periode}")

    @st.cache_data(ttl=300)
    def get_kategori_cached(tgl):
        return anggaran.get_pengeluaran_per_kategori(tanggal=tgl)

    with st.spinner("Memuat ringkasan kategori..."):
        dict_per_kategori = get_kategori_cached(tanggal_filter)

    if not dict_per_kategori:
        st.info("Tidak ada data untuk periode ini.")
    else:
        try:
            data_kategori = [{"Kategori": k, "Total": v} for k, v in dict_per_kategori.items()]
            df_kategori = (
                pd.DataFrame(data_kategori)
                .sort_values(by="Total", ascending=False)
                .reset_index(drop=True)
            )
            df_kategori['Total (Rp)'] = df_kategori['Total'].apply(format_rp)

            col_kat1, col_kat2 = st.columns(2)
            with col_kat1:
                st.write("**Tabel:**")
                st.dataframe(df_kategori[['Kategori', 'Total (Rp)']],
                             hide_index=True, use_container_width=True)
            with col_kat2:
                st.write("**Grafik:**")
                st.bar_chart(df_kategori.set_index('Kategori')['Total'],
                             use_container_width=True)
        except Exception as e:
            st.error(f"Gagal menampilkan ringkasan: {e}")


# ═══════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA - Navigasi & Sidebar
# ═══════════════════════════════════════════════════════════════════════
def main():
    st.sidebar.title("💰 Catatan Pengeluaran")
    menu_pilihan = st.sidebar.radio(
        "Pilih Menu:",
        ["Tambah", "Riwayat", "Ringkasan"],
        key="menu_utama"
    )
    st.sidebar.markdown("---")
    st.sidebar.info("Jobsheet 11 - Aplikasi Keuangan OOP")

    manajer = get_anggaran_manager()

    if menu_pilihan == "Tambah":
        halaman_input(manajer)
    elif menu_pilihan == "Riwayat":
        halaman_riwayat(manajer)
    elif menu_pilihan == "Ringkasan":
        halaman_ringkasan(manajer)

    st.markdown("---")
    st.caption("Pengembangan Aplikasi Berbasis OOP | Jobsheet 11")


if __name__ == "__main__":
    main()