# 99 — Sık Sorulan Sorular (Genel)

Bu belge modüller arası genel soruları kapsar. Modüle özgü sorular ilgili modül belgelerinde.

---

## Sisteme Erişim ve Kullanıcı

**S: Parolamı unuttum, ne yapmalıyım?**
C: IT sorumlusunu arayın. Kesinlikle e-posta ile paylaşmayın. Reset sonrası yeni geçici parola verilir, ilk girişte değiştirmelisiniz.

**S: Sistem hangi tarayıcıda çalışır?**
C: Chrome, Firefox, Edge (son 2 sürüm). Safari sınırlı test edildi. Internet Explorer desteklenmez.

**S: Mobil telefondan giriş yapabilir miyim?**
C: Evet — responsive tasarım. Ancak fatura kesimi gibi karmaşık formlar için PC/tablet önerilir.

**S: Aynı hesabı iki bilgisayardan aynı anda kullanabilir miyim?**
C: Teknik olarak mümkün ama önerilmez. Audit trail karışabilir. Farklı hesap açtırın.

**S: Sistem yavaşladı, ne yapmalıyım?**
C:
1. Ctrl+F5 ile hard refresh
2. Tarayıcı önbelleği temizle (Ctrl+Shift+Del)
3. Farklı tarayıcı dene
4. IT'ye bildir (belirli saatlerde yavaşlama pattern varsa)

**S: Ekranımdaki her şey Fransızca çıkıyor ama ben Türkçe istiyorum?**
C: Tarayıcı dil ayarları:
- Chrome → Ayarlar → Dil → Türkçe'yi ekle ve öne al
- Sonra sayfa yenile

Sistemde tüm arayüz metinleri iki dilli — dil ayarına göre otomatik değişir.

---

## Yetkiler ve Roller

**S: Bir sayfaya girmek istediğimde "Yetkiniz yok" hatası alıyorum?**
C: Rolünüzde o modüle erişim yok. Yöneticinizle görüşün. Ör. muhasebeci üretim modülüne varsayılan olarak giremez.

**S: Rolüm değişti ama hala eski yetkiler görünüyor?**
C: Oturumu kapatıp yeniden girin. Django session cache'i yeniler.

**S: Yönetici olarak birine yetki nasıl veririm?**
C: Admin → `/admin/auth/user/` → kullanıcı seç → Groups kısmında ilgili rol grubunu ekle.

**S: Bir kullanıcıyı geçici olarak pasifleştirebilir miyim?**
C: Evet. Admin → User → **is_active** işaretini kaldır. Silmek yerine bunu yapın (audit trail için).

---

## Veri Girişi ve Format

**S: Sayıları nasıl girmeliyim: 1234.56 mı 1.234,56 mı?**
C: **Girerken** noktalı (Excel gibi): `1234.56`. Sistem otomatik olarak `1.234,56` gösterir.

**S: Tarih formatı ne olmalı?**
C: Input alanları HTML5 date picker kullanır — takvimden seçin. Manuel yazarken: `YYYY-MM-DD` (ör. `2026-08-22`).

**S: Bir metin alanında satır kırma nasıl?**
C: TextField'lar (çok satırlı) Enter tuşuna basınca satır kırar. CharField'lar (tek satır) kırılmaz.

**S: Türkçe/Arapça karakter sorun oluyor mu?**
C: Sistem UTF-8 — Türkçe (ğ, ş, ı, ö, ü, ç), Arapça, Fransızca aksanlı harfler (é, à, ç) sorunsuz çalışır.

**S: PDF/JPG dosyası yüklerken hata alıyorum?**
C:
- Max boyut: 10 MB
- Kabul edilen: PDF, JPG, PNG (dosya uzantısı doğru olmalı)
- Şüpheli isim (özel karakter, boşluk) → yeniden adlandırın

---

## Fatura ve Belge

**S: Fatura kestikten sonra düzeltebilir miyim?**
C: Sadece **DRAFT** durumundaysa. POSTED sonrası düzeltme yapılamaz — alacak dekontu (avoir) veya ters kayıt gerekir.

**S: PDF çıktısı yazıcıya gönderilirken formatting bozuluyor?**
C: PDF olarak yazdırın (Ctrl+P → Hedef: PDF olarak kaydet). Direkt yazıcı için Firefox daha iyi renderleyebilir.

**S: Fatura numarası atlatabilir miyim?**
C: Hayır — Cezayir yasası (DGI) gereği fatura numaraları sürekli ve boşluksuz olmalı. Sistem otomatik sıra üretir.

**S: Aynı belgeden birden fazla kopya oluşturabilir miyim?**
C: PDF olarak birden fazla kopya alabilirsiniz (yazdırıp fotokopi). Sistemde her belge tekildir.

---

## Ödeme ve Cari

**S: Ödeme kaydettim ama fatura hala 'DRAFT' görünüyor?**
C: Faturayı önce **POSTED** durumuna getirmelisiniz (muhasebede işlem — dönem açık olmalı). Sonra ödeme kabul edilir.

**S: Çek karşılıksız çıktı, nasıl işlerim?**
C: Payment kaydında `check_status` → `BOUNCED`, `check_bounce_reason` doldur. Fatura otomatik `PARTIALLY_PAID`'a döner.

**S: Bir müşteriye avans verdim ama başka müşterinin faturasına tahsis etmek istiyorum?**
C: Sistem izin vermez — avans sadece kendi müşterisine tahsis edilebilir. Yanlış müşteriye avans verdiyseniz iade edip yeniden kaydedin.

**S: Cari hesap raporunda bakiye eksi çıkıyor?**
C: Alacaklıyız değil borçluyuz demektir — müşteri fazla ödeme yaptı veya avans ödendi. İnceleyip düzeltin.

---

## Üretim ve Kalite

**S: Bir batch başlattım ama parti başlat butonu bulamadım?**
C: Emir detay sayfasında besoins théoriques tablosunun altında. Eğer buton görünmüyorsa: stok yetersiz veya emir statüsü uygun değil.

**S: SCADA'dan batch gelmedi, üretim ne olacak?**
C: Manuel olarak batch başlatın (admin → ProductionBatch → add). SCADA sorununu IT/entegratöre bildirin.

**S: Bir batch RELEASED yapıldıktan sonra REJECT'e çevrilebilir mi?**
C: Teknik olarak evet ama audit trail için karmaşık. Öncelikle NCR açın, kalite müdürü kararı alın, sonra durum değiştirin. Sebep mutlaka yazılmalı.

**S: Test sonucu FAIL yazdım ama batch RELEASED oldu?**
C: QCTestResult vs Batch status ayrı — ilişki manuel. QA sorumlusu batch'i QC_HOLD'a çekmeli, sonra RELEASED değil REJECTED yapmalı. Kural: her FAIL sonrası batch REJECTED olmalı (mühendislik takdiri hariç).

**S: SDS PDF çıktısı çok uzun (10+ sayfa), kısaltabilir miyim?**
C: SDS 16 bölüm yasal olarak zorunlu. Her bölüm boşsa sistem "[not filled]" yazar. En azından "N/A" veya "Not applicable" yazın — daha temiz görünür.

---

## Yasal Uyum

**S: DoP olmadan Cezayir'de satabilir miyim?**
C: Cezayir'de zorunlu değil (yerel pazar). Ama EU'ya ihracat yapıyorsanız kesinlikle DoP + CE marking + CoC gerekli.

**S: REACH kaydı Cezayir üreticisi olarak gerekli mi?**
C: Cezayir'de üretip Cezayir'de satıyorsanız hayır. EU'ya ihracat yapıyorsanız Only Representative (OR) atamak veya ithalatçınızın kayıtlı olması gerekir.

**S: FPC audit'te başarısız olduk, sertifika iptal olur mu?**
C: Bağlıdır — NB politikasına ve NC şiddetine. Genelde `CONDITIONAL` verilir, 60-90 gün corrective action süresi. Sürede düzeltilmezse `SUSPENDED`, sonra `REVOKED`.

**S: SDS'i her yıl güncellemem gerekiyor mu?**
C: Yasal zorunlu değil ama önerilen. `next_review_date` ile takip edin. Formül değişikliği + yasal değişiklik durumunda **derhal** yeni versiyon.

---

## Rapor ve Analiz

**S: Bir raporu Excel olarak indirebilir miyim?**
C: Şu an sınırlı. Admin listelerinde bazı export butonları var. Portal raporları için ekran görüntüsü + Ctrl+P (PDF) kullanın. Excel export gelecek sürümlerde.

**S: Ay sonu snapshot alabilir miyim?**
C: Şu an manuel — her ay sonu raporları PDF olarak yazdırıp arşivleyin. Otomatik snapshot yakında.

**S: KPI rakamları neden farklı yerlerde farklı?**
C: Her rapor farklı zaman aralığı kullanabilir (bugün / bu ay / son 30 gün). Tanımı okuyup uygun karşılaştırma yapın.

**S: Cari hesap özetim yanlış görünüyor?**
C: Muhtemel sebepler:
- Bir fatura POSTED değil (DRAFT'ta kalmış)
- Bir ödeme yanlış müşteriye kaydedilmiş
- Avans kaydı eksik

IT + muhasebeye bildirin.

---

## Yedekleme ve Güvenlik

**S: Verilerim yedekleniyor mu?**
C: Evet — IT sorumlusu günlük otomatik yedek alıyor. Kritik veriniz varsa doğrulatmak için IT'ye sorun.

**S: Bir kayıt yanlışlıkla sildim, geri alabilir miyim?**
C: Bağlıdır. Bazı kayıtlar (Invoice, Payment, StockMovement) audit trail için silinmez — durum "CANCELLED" yapılır. Diğerleri Django admin'de silinebilir ama geri gelmez. IT'ye başvurun (yedekten geri getirilebilir).

**S: Kişisel bilgilerim nasıl korunuyor?**
C: Sistem KVKK/GDPR ilkelerine göre tasarlandı. Parolanız hash'lenmiş saklanır, kimse görüntüleyemez. IT'nin bile parolanıza erişimi yok (sadece reset yapabilir).

---

## Güncelleme ve Bakım

**S: Sistem güncellendi, arayüz farklı görünüyor?**
C: Normal. Değişiklik notları yeni özellikleri açıklar. IT bilgilendirme yapmalı. Sorun yaşıyorsanız IT'ye bildir.

**S: Yeni özellik istiyorum, nasıl talep ederim?**
C: IT sorumlusuna e-posta atın. Öneri:
- Mevcut sorunu tanımla
- İstenen özelliği açıkla
- Kullanım senaryosunu ver

**S: Sistem bakımı ne zaman yapılıyor?**
C: Genelde hafta sonu / gece — IT önceden duyurur. Kritik güncellemeler için 15 dk süreli bakım normaldir.

---

## Diğer

**S: Bu belge güncellendiğinde nasıl haber alacağım?**
C: IT / kalite ekibi e-posta gönderir. Bu klasördeki (`personel_egitimi/`) belgeler versiyonlanır — son güncelleme tarihini kontrol edin.

**S: Eğitim materyali yeterli değil, ek eğitim istiyorum?**
C: Modül sorumlunuza + kalite müdürüne bildir. Yılda 1-2 defa yenilenmiş eğitim yapılması standart.

**S: Sistemi öğrenmek için ne kadar zaman ayırmalıyım?**
C: Rol bazlı:
- İlk hafta: kendi rolünüzün belgesi + pratik (10-15 saat)
- İlk ay: gerçek işleri sistemden yaparak öğrenme
- 3 ay: sistemi rahatça kullanır durumda

**S: Ekran görüntüsü kimse görmesin diye şifreleyebilir miyim?**
C: Windows Snip & Sketch veya benzeri araçları kullanın. Sistem içinden ekran görüntüsü izleme özelliği yok.

---

## Acil Yardım

**Kritik sorun mu?** (üretim durmuş, fatura kesilemiyor, kritik hata)

1. **İlk 5 dk:** Sayfayı yenile, oturumu kapat/aç
2. **Sonraki 10 dk:** Farklı tarayıcı, IT'ye e-posta
3. **Devam ediyor mu?** Acil hattı ara: **[ACIL_TELEFON]**

Detaylı hata için ekran görüntüsü + hata mesajı + hangi işlemi yaparken oldu bilgisiyle IT'ye başvurun.

---

**Belge sürümü:** 1.0
**Son güncelleme:** 22 Ağustos 2026
