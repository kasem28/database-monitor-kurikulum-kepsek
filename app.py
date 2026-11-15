import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import os
import io
import uuid
import gspread

# Konfigurasi Halaman
st.set_page_config(
    page_title="Sistem Monitoring Kurikulum & Jurnal Mengajar",
    page_icon="??",
    layout="wide"
)

# Zona Waktu WIB (UTC+7)
WIB = timezone(timedelta(hours=7))

def sekarang_wib():
    return datetime.now(WIB)

# Data Default Awal (Digunakan saat inisialisasi pertama kali)
DEFAULT_MASTER = {
    "Nama_Guru": [
        "Ahmad Fauzi, S.Pd.",
        "Siti Aminah, S.P., Gr.",
        "Budi Santoso, M.Pd.",
        "Nurul Hidayah, S.Si.",
        "Rizki Pratama, S.Kom."
    ],
    "Kelas": [
        "X APHP 1", "X APHP 2",
        "XI APHP 1", "XI APHP 2",
        "XII APHP 1", "XII APHP 2"
    ],
    "Mata_Pelajaran": [
        "Dasar-Dasar Agriteknologi Pengolahan Hasil Pertanian",
        "Keamanan Pangan, Penyimpanan, dan Penggudangan",
        "Produksi Hasil Nabati",
        "Produksi Hasil Hewani",
        "Produk Kreatif dan Kewirausahaan",
        "Matematika",
        "Bahasa Indonesia",
        "Bahasa Inggris"
    ]
}

KOLOM_JURNAL = [
    "ID_Sesi", "Tanggal", "Nama_Guru", "Kelas", "Mata_Pelajaran",
    "Jam_Masuk", "Jam_Keluar", "Durasi_Menit", "Materi", "Status"
]

KOLOM_MASTER = ["Nama_Guru", "Kelas", "Mata_Pelajaran"]

FILE_JURNAL_LOKAL = "jurnal_mengajar.csv"
FILE_MASTER_LOKAL = "master_data.csv"

# --- KONEKSI GOOGLE SHEETS ---
def get_spreadsheet():
    """Membuka objek Spreadsheet utama jika st.secrets tersedia."""
    if "gcp_service_account" in st.secrets and "spreadsheet_id" in st.secrets:
        try:
            gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
            return gc.open_by_key(st.secrets["spreadsheet_id"])
        except Exception as e:
            st.error(f"Gagal terhubung ke Google Sheets: {e}")
            return None
    return None

def get_ws_jurnal(sh):
    ws = sh.sheet1
    if not ws.row_values(1):
        ws.append_row(KOLOM_JURNAL)
    return ws

def get_ws_master(sh):
    try:
        ws = sh.worksheet("Master_Data")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="Master_Data", rows="200", cols="5")
        baris_awal = bangun_baris_master(
            DEFAULT_MASTER["Nama_Guru"],
            DEFAULT_MASTER["Kelas"],
            DEFAULT_MASTER["Mata_Pelajaran"]
        )
        ws.update(values=[KOLOM_MASTER] + baris_awal, range_name="A1")
    return ws

def bangun_baris_master(list_guru, list_kelas, list_mapel):
    """Menyusun tiga list berbeda panjang menjadi baris tabel seragam."""
    max_len = max(len(list_guru), len(list_kelas), len(list_mapel), 1)
    rows = []
    for i in range(max_len):
        g = list_guru[i] if i < len(list_guru) else ""
        k = list_kelas[i] if i < len(list_kelas) else ""
        m = list_mapel[i] if i < len(list_mapel) else ""
        rows.append([g, k, m])
    return rows

# --- FUNGSI BACA & SIMPAN MASTER DATA ---
@st.cache_data(ttl=60, show_spinner=False)
def muat_master_data():
    sh = get_spreadsheet()
    if sh is not None:
        ws = get_ws_master(sh)
        values = ws.get_all_values()
        if len(values) <= 1:
            return DEFAULT_MASTER.copy()
        headers = values[0]
        rows = values[1:]
        hasil = {"Nama_Guru": [], "Kelas": [], "Mata_Pelajaran": []}
        for col_name in KOLOM_MASTER:
            if col_name in headers:
                idx = headers.index(col_name)
                items = [
                    row[idx].strip()
                    for row in rows
                    if len(row) > idx and row[idx].strip()
                ]
                # Hapus duplikat dengan mempertahankan urutan
                hasil[col_name] = list(dict.fromkeys(items))
        return hasil
    else:
        if os.path.exists(FILE_MASTER_LOKAL):
            df_m = pd.read_csv(FILE_MASTER_LOKAL, dtype=str).fillna("")
            return {
                col: list(dict.fromkeys([x.strip() for x in df_m[col].tolist() if x.strip()]))
                for col in KOLOM_MASTER
            }
        return DEFAULT_MASTER.copy()

def simpan_master_data(list_guru, list_kelas, list_mapel):
    baris = bangun_baris_master(list_guru, list_kelas, list_mapel)
    sh = get_spreadsheet()
    if sh is not None:
        ws = get_ws_master(sh)
        ws.clear()
        ws.update(values=[KOLOM_MASTER] + baris, range_name="A1")
    else:
        df_m = pd.DataFrame(baris, columns=KOLOM_MASTER)
        df_m.to_csv(FILE_MASTER_LOKAL, index=False)
    muat_master_data.clear()

# --- FUNGSI BACA & SIMPAN JURNAL MENGAJAR ---
@st.cache_data(ttl=30, show_spinner=False)
def muat_data_jurnal():
    sh = get_spreadsheet()
    if sh is not None:
        ws = get_ws_jurnal(sh)
        values = ws.get_all_values()
        if len(values) <= 1:
            return pd.DataFrame(columns=KOLOM_JURNAL)
        headers = values[0]
        rows = values[1:]
        # Pastikan panjang setiap baris sama dengan header
        normalized_rows = [
            row + [""] * (len(headers) - len(row)) if len(row) < len(headers) else row[:len(headers)]
            for row in rows
        ]
        df = pd.DataFrame(normalized_rows, columns=headers)
        for col in KOLOM_JURNAL:
            if col not in df.columns:
                df[col] = ""
        return df[KOLOM_JURNAL]
    else:
        if os.path.exists(FILE_JURNAL_LOKAL):
            return pd.read_csv(FILE_JURNAL_LOKAL, dtype=str).fillna("")
        return pd.DataFrame(columns=KOLOM_JURNAL)

def simpan_sesi_baru(data_dict):
    sh = get_spreadsheet()
    baris = [str(data_dict.get(k, "")) for k in KOLOM_JURNAL]
    if sh is not None:
        ws = get_ws_jurnal(sh)
        ws.append_row(baris)
    else:
        df = muat_data_jurnal()
        df_baru = pd.DataFrame([data_dict])
        df = pd.concat([df, df_baru], ignore_index=True)
        df.to_csv(FILE_JURNAL_LOKAL, index=False)
    muat_data_jurnal.clear()

def selesaikan_sesi(id_sesi, jam_keluar_str, durasi_menit, materi):
    sh = get_spreadsheet()
    if sh is not None:
        ws = get_ws_jurnal(sh)
        daftar_id = ws.col_values(1)
        if id_sesi in daftar_id:
            row_idx = daftar_id.index(id_sesi) + 1
            ws.update(
                values=[[jam_keluar_str, str(durasi_menit), materi, "Selesai"]],
                range_name=f"G{row_idx}:J{row_idx}"
            )
            muat_data_jurnal.clear()
            return True
        return False
    else:
        df = muat_data_jurnal()
        mask = df["ID_Sesi"] == id_sesi
        if mask.any():
            df.loc[mask, "Jam_Keluar"] = jam_keluar_str
            df.loc[mask, "Durasi_Menit"] = str(durasi_menit)
            df.loc[mask, "Materi"] = materi
            df.loc[mask, "Status"] = "Selesai"
            df.to_csv(FILE_JURNAL_LOKAL, index=False)
            muat_data_jurnal.clear()
            return True
        return False

def hitung_durasi(jam_masuk_str, jam_keluar_str):
    fmt = "%H:%M"
    t1 = datetime.strptime(jam_masuk_str[:5], fmt)
    t2 = datetime.strptime(jam_keluar_str[:5], fmt)
    selisih = int((t2 - t1).total_seconds() // 60)
    return max(selisih, 0)

def to_excel(df_jurnal, df_rekap):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_rekap.to_excel(writer, index=False, sheet_name="Himpunan_Per_Mapel")
        df_jurnal.to_excel(writer, index=False, sheet_name="Log_Detail_Mengajar")
    return output.getvalue()

# --- MUAT MASTER DATA DINAMIS ---
master = muat_master_data()
OPSI_GURU = ["Pilih Nama Guru..."] + master["Nama_Guru"]
OPSI_KELAS = ["Pilih Kelas..."] + master["Kelas"]
OPSI_MAPEL = ["Pilih Mata Pelajaran..."] + master["Mata_Pelajaran"]

# --- ANTARMUKA APLIKASI ---
st.title("?? Sistem Monitoring Kurikulum & Jurnal Mengajar")

sh_aktif = get_spreadsheet()
mode_penyimpanan = "?? Terhubung ke Google Sheets (Master Dinamis)" if sh_aktif else "?? Mode Penyimpanan Lokal (CSV)"
st.caption(f"Waktu Server (WIB): **{sekarang_wib().strftime('%d-%m-%Y %H:%M')}** | Status Database: {mode_penyimpanan}")

tab_guru, tab_kurikulum = st.tabs(["????? Menu Input Guru", "?? Dashboard Kurikulum"])

# ==========================================
# TAB 1: MENU INPUTAN GURU
# ==========================================
with tab_guru:
    st.subheader("Jurnal Kehadiran & Materi Mengajar")
    metode_input = st.radio(
        "Pilih Alur Pengisian:",
        [
            "1?? Check-In Masuk Kelas (Real-Time)",
            "2?? Check-Out Selesai Mengajar & Isi Materi",
            "3?? Input Lengkap Sekaligus (Masuk & Keluar)"
        ],
        horizontal=True
    )

    now = sekarang_wib()
    tgl_hari_ini = now.strftime("%Y-%m-%d")

    # --- OPSI 1: CHECK-IN MASUK KELAS ---
    if metode_input.startswith("1??"):
        with st.form("form_checkin", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                guru = st.selectbox("Nama Guru", OPSI_GURU)
                kelas = st.selectbox("Kelas", OPSI_KELAS)
            with col2:
                mapel = st.selectbox("Mata Pelajaran", OPSI_MAPEL)
                jam_masuk = st.time_input("Waktu Masuk Kelas", value=now.time())

            materi_awal = st.text_input(
                "Rencana Materi / Topik (Bisa dilengkapi saat keluar)",
                placeholder="Contoh: Sanitasi Industri Pangan"
            )
            submit_in = st.form_submit_button("? Catat Masuk Kelas", use_container_width=True, type="primary")

            if submit_in:
                if guru == "Pilih Nama Guru..." or kelas == "Pilih Kelas..." or mapel == "Pilih Mata Pelajaran...":
                    st.warning("Harap pilih Nama Guru, Kelas, dan Mata Pelajaran terlebih dahulu.")
                else:
                    sesi_baru = {
                        "ID_Sesi": str(uuid.uuid4())[:8].upper(),
                        "Tanggal": tgl_hari_ini,
                        "Nama_Guru": guru,
                        "Kelas": kelas,
                        "Mata_Pelajaran": mapel,
                        "Jam_Masuk": jam_masuk.strftime("%H:%M"),
                        "Jam_Keluar": "-",
                        "Durasi_Menit": "0",
                        "Materi": materi_awal if materi_awal else "(Sedang berlangsung)",
                        "Status": "Sedang Mengajar"
                    }
                    simpan_sesi_baru(sesi_baru)
                    st.success(f"Check-in berhasil! **{guru}** tercatat masuk di kelas **{kelas}** pada pukul **{jam_masuk.strftime('%H:%M')}**.")

    # --- OPSI 2: CHECK-OUT SELESAI MENGAJAR ---
    elif metode_input.startswith("2??"):
        df_all = muat_data_jurnal()
        df_aktif = df_all[df_all["Status"] == "Sedang Mengajar"]

        if df_aktif.empty:
            st.info("Tidak ada sesi kelas yang berstatus 'Sedang Mengajar' saat ini.")
        else:
            opsi_sesi = {
                f"{row['Tanggal']} | {row['Kelas']} - {row['Nama_Guru']} ({row['Mata_Pelajaran']}) - Masuk {row['Jam_Masuk']}": row
                for _, row in df_aktif.iterrows()
            }
            pilihan_label = st.selectbox("Pilih Sesi Mengajar yang Akan Diselesaikan:", list(opsi_sesi.keys()))
            data_terpilih = opsi_sesi[pilihan_label]

            with st.form("form_checkout"):
                jam_keluar = st.time_input("Waktu Keluar Kelas", value=now.time())
                materi_akhir = st.text_area(
                    "Materi yang Diajarkan *",
                    value="" if data_terpilih["Materi"] == "(Sedang berlangsung)" else data_terpilih["Materi"],
                    placeholder="Tuliskan pokok bahasan / kegiatan praktikum yang telah dilaksanakan..."
                )
                submit_out = st.form_submit_button("?? Selesaikan Sesi & Simpan Materi", use_container_width=True, type="primary")

                if submit_out:
                    jam_keluar_str = jam_keluar.strftime("%H:%M")
                    if jam_keluar_str <= data_terpilih["Jam_Masuk"]:
                        st.error("Waktu keluar harus lebih akhir daripada waktu masuk kelas.")
                    elif not materi_akhir.strip():
                        st.warning("Harap isi materi yang diajarkan sebelum menyimpan.")
                    else:
                        durasi = hitung_durasi(data_terpilih["Jam_Masuk"], jam_keluar_str)
                        sukses = selesaikan_sesi(data_terpilih["ID_Sesi"], jam_keluar_str, durasi, materi_akhir.strip())
                        if sukses:
                            st.success(f"Sesi selesai! Durasi mengajar: **{durasi} menit**. Data telah terhimpun di Dashboard Kurikulum.")
                            st.rerun()

    # --- OPSI 3: INPUT LENGKAP SEKALIGUS ---
    else:
        with st.form("form_lengkap", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                tgl_input = st.date_input("Tanggal Mengajar", value=now.date())
                guru = st.selectbox("Nama Guru", OPSI_GURU)
                kelas = st.selectbox("Kelas", OPSI_KELAS)
            with col2:
                mapel = st.selectbox("Mata Pelajaran", OPSI_MAPEL)
                c_in, c_out = st.columns(2)
                with c_in:
                    jam_masuk = st.time_input("Waktu Masuk", value=now.time())
                with c_out:
                    jam_keluar = st.time_input("Waktu Keluar", value=now.time())

            materi_lengkap = st.text_area("Materi yang Diajarkan *", placeholder="Tuliskan materi pelajaran yang disampaikan...")
            submit_all = st.form_submit_button("?? Simpan Jurnal Mengajar", use_container_width=True, type="primary")

            if submit_all:
                jam_in_str = jam_masuk.strftime("%H:%M")
                jam_out_str = jam_keluar.strftime("%H:%M")
                if guru == "Pilih Nama Guru..." or kelas == "Pilih Kelas..." or mapel == "Pilih Mata Pelajaran...":
                    st.warning("Harap lengkapi Nama Guru, Kelas, dan Mata Pelajaran.")
                elif jam_out_str <= jam_in_str:
                    st.error("Waktu keluar harus lebih besar daripada waktu masuk.")
                elif not materi_lengkap.strip():
                    st.warning("Materi yang diajarkan wajib diisi.")
                else:
                    durasi = hitung_durasi(jam_in_str, jam_out_str)
                    sesi_lengkap = {
                        "ID_Sesi": str(uuid.uuid4())[:8].upper(),
                        "Tanggal": tgl_input.strftime("%Y-%m-%d"),
                        "Nama_Guru": guru,
                        "Kelas": kelas,
                        "Mata_Pelajaran": mapel,
                        "Jam_Masuk": jam_in_str,
                        "Jam_Keluar": jam_out_str,
                        "Durasi_Menit": str(durasi),
                        "Materi": materi_lengkap.strip(),
                        "Status": "Selesai"
                    }
                    simpan_sesi_baru(sesi_lengkap)
                    st.success(f"Jurnal mengajar **{mapel}** ({kelas}) berhasil disimpan.")

# ==========================================
# TAB 2: DASHBOARD KURIKULUM
# ==========================================
with tab_kurikulum:
    pin_kurikulum = st.secrets.get("pin_kurikulum", "1234")
    pin_input = st.text_input("Masukkan PIN Kurikulum untuk Membuka Dashboard (Default: 1234):", type="password")

    if pin_input != str(pin_kurikulum):
        st.info("Masukkan PIN Kurikulum di atas untuk memantau kehadiran guru, himpunan mata pelajaran, dan pengelolaan master data.")
    else:
        if st.button("?? Segarkan Semua Data (Jurnal & Master)"):
            muat_data_jurnal.clear()
            muat_master_data.clear()
            st.rerun()

        sub_pantau, sub_master = st.tabs(["?? Pantauan & Rekap Mapel", "?? Kelola Master Guru, Kelas & Mapel"])

        # --- SUB-TAB 1: PANTAUAN & REKAP MAPEL ---
        with sub_pantau:
            df = muat_data_jurnal()

            if df.empty:
                st.warning("Belum ada data jurnal mengajar yang masuk.")
            else:
                df["Durasi_Menit"] = pd.to_numeric(df["Durasi_Menit"], errors="coerce").fillna(0).astype(int)
                tgl_str_today = sekarang_wib().strftime("%Y-%m-%d")
                df_hari_ini = df[df["Tanggal"] == tgl_str_today]

                st.markdown(f"### ?? Pantauan Aktivitas Kelas Hari Ini ({tgl_str_today})")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Sedang Mengajar (Live)", len(df_hari_ini[df_hari_ini["Status"] == "Sedang Mengajar"]))
                m2.metric("Sesi Selesai Hari Ini", len(df_hari_ini[df_hari_ini["Status"] == "Selesai"]))
                m3.metric("Kelas Terisi Hari Ini", df_hari_ini["Kelas"].nunique())
                m4.metric("Total Mapel Tercatat", df["Mata_Pelajaran"].nunique())

                if not df_hari_ini.empty:
                    st.dataframe(
                        df_hari_ini[["Status", "Jam_Masuk", "Jam_Keluar", "Kelas", "Nama_Guru", "Mata_Pelajaran", "Materi"]],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Belum ada guru yang melakukan check-in hari ini.")

                st.divider()

                st.markdown("### ?? Himpunan & Rekapitulasi Seluruh Mata Pelajaran")
                f1, f2, f3 = st.columns(3)
                with f1:
                    filter_kelas = st.multiselect("Filter Kelas", options=sorted(df["Kelas"].unique()))
                with f2:
                    filter_mapel = st.multiselect("Filter Mata Pelajaran", options=sorted(df["Mata_Pelajaran"].unique()))
                with f3:
                    filter_guru = st.multiselect("Filter Guru", options=sorted(df["Nama_Guru"].unique()))

                df_filtered = df.copy()
                if filter_kelas:
                    df_filtered = df_filtered[df_filtered["Kelas"].isin(filter_kelas)]
                if filter_mapel:
                    df_filtered = df_filtered[df_filtered["Mata_Pelajaran"].isin(filter_mapel)]
                if filter_guru:
                    df_filtered = df_filtered[df_filtered["Nama_Guru"].isin(filter_guru)]

                rekap_mapel = (
                    df_filtered.groupby(["Mata_Pelajaran", "Kelas"], as_index=False)
                    .agg(
                        Jumlah_Pertemuan=("ID_Sesi", "count"),
                        Total_Menit=("Durasi_Menit", "sum"),
                        Guru_Pengampu=("Nama_Guru", lambda x: ", ".join(sorted(set(x)))),
                        Riwayat_Materi=("Materi", lambda x: " | ".join([m for m in x if m != "(Sedang berlangsung)"]))
                    )
                )
                rekap_mapel["Total_Jam"] = (rekap_mapel["Total_Menit"] / 60).round(2)

                st.markdown("**Ringkasan Terhimpun per Mata Pelajaran & Kelas:**")
                st.dataframe(
                    rekap_mapel[["Mata_Pelajaran", "Kelas", "Guru_Pengampu", "Jumlah_Pertemuan", "Total_Jam", "Riwayat_Materi"]],
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("**Log Detail Seluruh Jurnal Mengajar:**")
                df_sorted = df_filtered.sort_values(by=["Tanggal", "Jam_Masuk"], ascending=False)
                st.dataframe(df_sorted, use_container_width=True, hide_index=True)

                excel_bytes = to_excel(df_sorted, rekap_mapel)
                st.download_button(
                    label="?? Unduh Laporan Kurikulum (2 Sheet Excel .xlsx)",
                    data=excel_bytes,
                    file_name=f"Rekap_Kurikulum_{tgl_str_today}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        # --- SUB-TAB 2: KELOLA MASTER DATA ---
        with sub_master:
            st.markdown("### ?? Pengaturan Daftar Guru, Kelas & Mata Pelajaran")
            st.caption("Perubahan di sini langsung memperbarui tab `Master_Data` di Google Sheets dan otomatis muncul di form input guru.")

            col_g, col_k, col_m = st.columns(3)

            # Kelola Guru
            with col_g:
                st.markdown("**????? Daftar Guru**")
                guru_baru = st.text_input("Tambah Nama Guru Baru", placeholder="Contoh: Drs. Hasanuddin")
                if st.button("? Tambah Guru", use_container_width=True):
                    if guru_baru.strip() and guru_baru.strip() not in master["Nama_Guru"]:
                        simpan_master_data(
                            master["Nama_Guru"] + [guru_baru.strip()],
                            master["Kelas"],
                            master["Mata_Pelajaran"]
                        )
                        st.success("Guru ditambahkan.")
                        st.rerun()

                guru_hapus = st.selectbox("Pilih Guru untuk Dihapus", ["-"] + master["Nama_Guru"])
                if st.button("??? Hapus Guru", use_container_width=True) and guru_hapus != "-":
                    simpan_master_data(
                        [g for g in master["Nama_Guru"] if g != guru_hapus],
                        master["Kelas"],
                        master["Mata_Pelajaran"]
                    )
                    st.warning(f"{guru_hapus} dihapus.")
                    st.rerun()
                st.dataframe(pd.DataFrame({"Nama Guru": master["Nama_Guru"]}), use_container_width=True, hide_index=True)

            # Kelola Kelas
            with col_k:
                st.markdown("**?? Daftar Kelas**")
                kelas_baru = st.text_input("Tambah Kelas Baru", placeholder="Contoh: XI APHP 3")
                if st.button("? Tambah Kelas", use_container_width=True):
                    if kelas_baru.strip() and kelas_baru.strip() not in master["Kelas"]:
                        simpan_master_data(
                            master["Nama_Guru"],
                            master["Kelas"] + [kelas_baru.strip()],
                            master["Mata_Pelajaran"]
                        )
                        st.success("Kelas ditambahkan.")
                        st.rerun()

                kelas_hapus = st.selectbox("Pilih Kelas untuk Dihapus", ["-"] + master["Kelas"])
                if st.button("??? Hapus Kelas", use_container_width=True) and kelas_hapus != "-":
                    simpan_master_data(
                        master["Nama_Guru"],
                        [k for k in master["Kelas"] if k != kelas_hapus],
                        master["Mata_Pelajaran"]
                    )
                    st.warning(f"{kelas_hapus} dihapus.")
                    st.rerun()
                st.dataframe(pd.DataFrame({"Kelas": master["Kelas"]}), use_container_width=True, hide_index=True)

            # Kelola Mata Pelajaran
            with col_m:
                st.markdown("**?? Daftar Mata Pelajaran**")
                mapel_baru = st.text_input("Tambah Mapel Baru", placeholder="Contoh: Pengendalian Mutu Hasil Pertanian")
                if st.button("? Tambah Mapel", use_container_width=True):
                    if mapel_baru.strip() and mapel_baru.strip() not in master["Mata_Pelajaran"]:
                        simpan_master_data(
                            master["Nama_Guru"],
                            master["Kelas"],
                            master["Mata_Pelajaran"] + [mapel_baru.strip()]
                        )
                        st.success("Mata pelajaran ditambahkan.")
                        st.rerun()

                mapel_hapus = st.selectbox("Pilih Mapel untuk Dihapus", ["-"] + master["Mata_Pelajaran"])
                if st.button("??? Hapus Mapel", use_container_width=True) and mapel_hapus != "-":
                    simpan_master_data(
                        master["Nama_Guru"],
                        master["Kelas"],
                        [m for m in master["Mata_Pelajaran"] if m != mapel_hapus]
                    )
                    st.warning(f"{mapel_hapus} dihapus.")
                    st.rerun()
                st.dataframe(pd.DataFrame({"Mata Pelajaran": master["Mata_Pelajaran"]}), use_container_width=True, hide_index=True)