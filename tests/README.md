# 瀏覽器功能測試

在儲存庫根目錄執行：

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
python3 -m unittest discover -s tests -v
```

若已安裝 Chromium，可用 `SAS_BROWSER_EXECUTABLE` 指定執行檔。測試會自動啟動僅綁定 `127.0.0.1` 的暫時 HTTP 伺服器，結束後關閉；不會送出示範資料或操作真實檔案。

涵蓋手動完整流程、Skill 加入／忽略分支、XML 開啟與另存、Windows 開始選單、檔案總管剪下／貼上／復原／拖曳、檢核與歸檔、草稿保留、視窗放大／收起／還原，以及非示範區的流程卡片、固定切換列、跳轉連結、重設、專注模式、工具提示、全螢幕與鍵盤操作。

完整流程使用桌機、平板、手機直向及橫向尺寸，包含觸控模擬；另測放大視窗與較短螢幕。回歸案例驗證欄位標題不遮擋 XML、步驟前進保留放大狀態、XML Enter 開啟、切換流程保留勾選與文字，以及取消檢核後不得直接歸檔。

執行環境為 Chromium；觸控模擬不等於實機 Safari／Firefox 測試。

逐步按鍵與分支檢查內容見 [BUTTON_CHECKLIST.md](BUTTON_CHECKLIST.md)。`test_buttons.py` 會逐一列舉代表性畫面的可見按鈕，點擊並驗證結果，同時檢查應停用的控制項；新增未涵蓋的啟用按鈕會使測試失敗。可設定 `SAS_BUTTON_AUDIT_JSON` 指定逐筆檢查結果的輸出路徑。
