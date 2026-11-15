import streamlit as st
import pandas as pd
from datetime import datetime

# Konfigurasi Halaman
st.set_page_config(page_title="Sistem Monitoring Kurikulum", page_icon="🏫", layout="wide")

# Inisialisasi Database Sederhana menggunakan Session State
if 'jurnal_mengajar' not in st.session_state:
    st.session_state.jurnal_mengajar = pd.DataFrame(columns=[
        'Tanggal', 'Nama Guru', 'Kelas', 'Mata Pelajaran', 
        'Jam Masuk', 'Jam Keluar', 'Materi / Pokok Bahasan', 
        'Status Kehadiran', 'Foto Dokumentasi'
    ])

# Navigasi Sidebar
st.sidebar.title("🏫 Portal Akademik")
menu = st.sidebar.radio("Pilih Menu:", [
    "Dashboard Kurikulum",
    "Input Jurnal Mengajar (Guru)"
])

# ==========================================
# HALAMAN 1: DASHBOARD KURIKULUM
# ==========================================
if menu == "Dashboard Kurikulum":
    st.title("📊 Dashboard Monitoring Kurikulum")
    st.write("Rekapitulasi real-time kehadiran guru dan ketercapaian materi pembelajaran di kelas.")
    st.markdown("---")

    df = st.session_state.jurnal_mengajar

    # Bagian Filter Data
    st.subheader("🔍 Filter Data Pembelajaran")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        filter_tanggal = st.date_input("Pilih Tanggal", datetime.now().date())
    with col_f2:
        daftar_kelas = ["Semua Kelas"] + sorted(df['Kelas'].unique().tolist()) if not df.empty else ["Semua Kelas"]
        filter_kelas = st.selectbox("Filter Kelas", daftar_kelas)
    with col_f3:
        daftar_guru = ["Semua Guru"] + sorted(df['Nama Guru'].unique().tolist()) if not df.empty else ["Semua Guru"]
        filter_guru = st.selectbox("Filter Nama Guru", daftar_guru)

    # Terapkan Filter ke DataFrame
    if not df.empty:
        df_filtered = df[df['Tanggal'] == filter_tanggal.strftime('%Y-%m-%d')]
        
        if filter_kelas != "Semua Kelas":
            df_filtered = df_filtered[df_filtered['Kelas'] == filter_kelas]
        if filter_guru != "Semua Guru":
            df_filtered = df_filtered[df_filtered['Nama Guru'] == filter_guru]

        # Metrik Ringkasan
        st.markdown("### Ringkasan Hari Ini")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Sesi Mengajar", f"{len(df_filtered)} Sesi")
        m2.metric("Guru Aktif Mengajar", f"{df_filtered['Nama Guru'].nunique()} Guru")
        m3.metric("Kelas Terisi", f"{df_filtered['Kelas'].nunique()} Kelas")

        st.markdown("### Daftar Jurnal Masuk")
        if not df_filtered.empty:
            st.dataframe(df_filtered, use_container_width=True)
            
            # Fitur Export Laporan ke CSV (bisa dibuka di Excel)
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Unduh Rekap Jurnal (CSV / Excel)",
                data=csv,
                file_name=f"rekap_kurikulum_{filter_tanggal.strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
            )
        else:
            st.warning("Tidak ada data pembelajaran pada tanggal atau filter yang dipilih.")
    else:
        st.info("Belum ada data jurnal mengajar yang diinput oleh guru.")

# ==========================================
# HALAMAN 2: INPUT JURNAL MENGAJAR (GURU)
# ==========================================
elif menu == "Input Jurnal Mengajar (Guru)":
    st.title("✍️ Form Jurnal Mengajar Guru")
    st.write("Silakan isi laporan kegiatan pembelajaran setelah menyelesaikan jam mengajar di kelas.")

    with st.form(key="form_jurnal_guru", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            tanggal = st.date_input("Tanggal Mengajar", datetime.now().date())
            nama_guru = st.text_input("Nama Lengkap & Gelar Guru")
            kelas = st.selectbox("Kelas", [
                "X APHP", "XI APHP", "XII APHP", 
                "X ATPH", "XI ATPH", "XII ATPH", 
                "X ATR", "XI ATR", "XII ATR"
            ])
            mapel = st.text_input("Mata Pelajaran")

        with col2:
            jam_masuk = st.time_input("Waktu Masuk Kelas", datetime.now().time())
            jam_keluar = st.time_input("Waktu Keluar Kelas", datetime.now().time())
            status = st.selectbox("Status Kehadiran", [
                "Hadir Mengajar", 
                "Tugas Mandiri (Guru Izin/Dinas Luar)", 
                "Praktikum Bengkel / Lab"
            ])
            foto_kegiatan = st.file_uploader("Upload Foto Kegiatan Kelas (Opsional)", type=["jpg", "jpeg", "png"])

        materi = st.text_area("Materi / Pokok Bahasan & Catatan Perkembangan Siswa")
        
        submit = st.form_submit_button("Kirim Laporan ke Kurikulum")

        if submit:
            if nama_guru and mapel and materi:
                nama_file = foto_kegiatan.name if foto_kegiatan is not None else "Tidak ada foto"
                
                data_baru = pd.DataFrame({
                    'Tanggal': [tanggal.strftime('%Y-%m-%d')],
                    'Nama Guru': [nama_guru],
                    'Kelas': [kelas],
                    'Mata Pelajaran': [mapel],
                    'Jam Masuk': [jam_masuk.strftime('%H:%M')],
                    'Jam Keluar': [jam_keluar.strftime('%H:%M')],
                    'Materi / Pokok Bahasan': [materi],
                    'Status Kehadiran': [status],
                    'Foto Dokumentasi': [nama_file]
                })
                
                st.session_state.jurnal_mengajar = pd.concat([st.session_state.jurnal_mengajar, data_baru], ignore_index=True)
                st.success(f"Terima kasih {nama_guru}! Jurnal mata pelajaran {mapel} untuk kelas {kelas} berhasil masuk ke Dashboard Kurikulum.")
            else:
                st.error("Mohon lengkapi Nama Guru, Mata Pelajaran, dan Materi yang diajarkan!")