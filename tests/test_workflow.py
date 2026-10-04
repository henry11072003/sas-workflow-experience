"""Offline browser regression checks for the standalone HTML.
Run: python3 -m unittest discover -s tests -v
Requires playwright and Chromium; SAS_BROWSER_EXECUTABLE may select a browser binary.
"""
import os
from pathlib import Path
import shutil
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright, expect

HTML = Path(__file__).resolve().parents[1] / 'SAS_workflow_experience.html'


class BrowserTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/SAS.html':
                    self.send_error(404)
                    return
                content = HTML.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def log_message(self, *args):
                pass

        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server_thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/SAS.html'
        cls.pw = sync_playwright().start()
        executable = os.environ.get('SAS_BROWSER_EXECUTABLE') or shutil.which('chromium')
        options = {'headless': True, 'args': ['--no-sandbox']}
        if executable:
            options['executable_path'] = executable
        cls.browser = cls.pw.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()

    def setUp(self):
        self.contexts = []
        self.errors = []
        self.new_page()

    def tearDown(self):
        for context in self.contexts:
            context.close()
        self.assertEqual([], self.errors, 'Unexpected browser JavaScript errors')

    def new_page(self, width=1366, height=768, touch=False, motion='reduce'):
        context = self.browser.new_context(viewport={'width': width, 'height': height},
                                          has_touch=touch, is_mobile=touch, reduced_motion=motion)
        self.contexts.append(context)
        self.page = context.new_page()
        self.page.set_default_timeout(7000)
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.goto(self.url)
        self.touch = touch
        return self.page

    def click(self, selector):
        control = self.page.locator(selector)
        control.tap() if self.touch else control.click()

    def action(self, name):
        self.click(f'[data-action="{name}"]')

    def native(self, name):
        self.click(f'[data-native="{name}"]')

    def step(self, title):
        expect(self.page.locator('#step-title')).to_have_text(title)
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))

    def manual(self, maximized=False):
        self.action('login')
        self.step('匯出照會資料')
        self.action('query')
        self.action('export')
        self.step('確認下載檔案')
        self.click('#mn-start-button')
        self.native('launch-excel')
        self.step('以 XML 表格匯入')
        self.click('[data-page="open"]')
        self.native('browse')
        self.native('pick-xml')
        self.native('open-xml')
        self.page.locator('input[value="readonly"]').check()
        self.native('import-xml')
        expect(self.page.locator('#mn-error')).to_contain_text('XML 表格')
        self.page.locator('input[value="table"]').check()
        self.native('import-xml')
        self.step('檢視資料並另存')
        self.native('backstage')
        self.click('[data-page="save"]')
        self.native('browse')
        self.page.locator('#mn-filetype').select_option('xml')
        self.native('save-workbook')
        expect(self.page.locator('#mn-error')).to_contain_text('Excel 活頁簿')
        self.page.locator('#mn-filetype').select_option('xlsx')
        self.native('save-workbook')
        self.step('建立樞紐分析表')
        self.action('create-pivot')
        expect(self.page.locator('#error')).to_contain_text('請勾選')
        for checkbox in self.page.locator('[data-pivot-field]').all():
            checkbox.check()
        self.action('create-pivot')
        self.step('篩選碼別與填表')
        if maximized:
            expect(self.page.locator('.window')).to_have_class('window app-excel is-maximized')
        for code in ['BB', 'DA', 'BA']:
            self.page.locator('#code-filter').select_option(code)
        self.page.locator('#accept-filter').select_option('yes')
        self.page.locator('#accept-filter').select_option('all')
        self.action('show-report')
        self.action('fill-report')
        expect(self.page.locator('#error')).to_contain_text('數字尚未正確')
        for index, pair in enumerate([(14, 11), (10, 8), (8, 6), (12, 9)]):
            for field, value in zip(['assigned', 'accepted'], pair):
                self.page.locator(f'#{field}-{index}').fill(str(value))
        self.action('show-pivot')
        self.action('show-report')
        expect(self.page.locator('#assigned-0')).to_have_value('14')
        self.action('fill-report')
        self.step('核對格式與數字')
        self.action('save-report')
        expect(self.page.locator('#error')).to_contain_text('三項')
        for checkbox in self.page.locator('#stage .review-check').all():
            checkbox.check()
        self.action('save-report')
        self.step('儲存完成')
        expect(self.page.locator('[data-file="11507_輪派報表.xlsx"]')).to_be_visible()
        expect(self.page.locator('[data-action="switch-skill"]')).to_be_visible()

    def skill(self, choice='1 加入', maximized=False):
        expect(self.page.locator('[data-action="place-xml"]')).to_be_disabled()
        self.click('#download-xml')
        for name in ['cut', 'go-input', 'paste']:
            self.click(f'[data-explorer="{name}"]')
        self.action('place-xml')
        self.step('執行 Skill')
        if maximized:
            expect(self.page.locator('.window')).to_have_class('window app-claw is-maximized')
        self.page.locator('#command').fill('/sas')
        self.click('#sas-option')
        self.action('clear-sas')
        self.page.locator('#command').fill('/sas-for-eden')
        self.click('#sas-option')
        self.page.locator('#command').fill('執行')
        self.click('#run-form button[type="submit"]')
        self.step('決定新單位')
        self.page.locator('#unit-reply').fill('2 加入')
        self.click('#unit-reply-form button')
        expect(self.page.locator('#unit-reply-error')).to_contain_text('目前只有編號 1')
        self.page.locator('#unit-reply').fill(choice)
        self.click('#unit-reply-form button')
        self.step('Excel 檢核與歸檔')
        expect(self.page.locator('#confirmation')).to_be_disabled()
        self.action('review')
        self.action('review-done')
        expect(self.page.locator('#review-error')).to_contain_text('三項')
        expect(self.page.locator('#review .notice')).to_contain_text('14/11' if '忽略' in choice else '26/20')
        for checkbox in self.page.locator('#review .review-check').all():
            checkbox.check()
        self.action('review-done')
        self.page.locator('#confirmation').fill('不確認，先別歸檔')
        self.click('#finalize-form button')
        expect(self.page.locator('#error')).to_contain_text('請明確輸入')
        self.page.locator('#confirmation').fill('確認無誤, 歸檔')
        self.click('#finalize-form button')
        self.step('完成')
        expect(self.page.get_by_role('heading', name='本月作業完成')).to_be_visible()


class WorkflowTest(BrowserTestCase):
    def test_complete_desktop_tablet_mobile_and_landscape(self):
        for width, height, touch in [(1366, 768, False), (768, 1024, True),
                                     (390, 664, True), (320, 568, True), (844, 390, True)]:
            with self.subTest(width=width, height=height, touch=touch):
                self.new_page(width, height, touch)
                self.manual()
                self.action('switch-skill')
                self.skill()
                self.page.once('dialog', lambda dialog: dialog.accept())
                self.click('#reset')
                self.skill('全部忽略')
                self.action('switch-original')
                self.step('儲存完成')

    def test_maximized_workflows_keep_controls_reachable(self):
        for width, height in [(1366, 768), (390, 664), (844, 390)]:
            with self.subTest(width=width):
                self.new_page(width, height)
                self.click('[data-window="maximize"]')
                self.manual(maximized=True)
                # Completion action is outside the application window and must remain clickable.
                self.action('switch-skill')
                self.click('[data-window="maximize"]')
                self.skill(maximized=True)

    def test_drafts_checks_and_revalidation(self):
        p = self.page
        p.evaluate('m.step=7;render()')  # Isolate the review screen; complete paths tested above.
        p.locator('#stage .review-check').first.check()
        self.click('#tab-original')
        expect(p.locator('#stage .review-check').first).to_be_checked()
        self.click('#tab-skill')
        self.click('#tab-original')
        expect(p.locator('#stage .review-check').first).to_be_checked()
        self.click('#tab-skill')
        p.evaluate("s.step=3;s.choice='add';render()")
        self.action('review')
        for checkbox in p.locator('#review .review-check').all():
            checkbox.check()
        self.action('review-done')
        p.locator('#confirmation').fill('確認無誤，歸檔')
        self.click('#tab-original')
        self.click('#tab-skill')
        expect(p.locator('#confirmation')).to_have_value('確認無誤，歸檔')
        self.action('review')
        expect(p.locator('#review .review-check:checked')).to_have_count(3)
        p.locator('#review .review-check').first.uncheck()
        self.action('close-review')
        expect(p.locator('#confirmation')).to_be_disabled()
        expect(p.locator('#finalize-form button')).to_be_disabled()
        self.action('review')
        p.locator('#review .review-check').first.check()
        self.action('review-done')
        expect(p.locator('#confirmation')).to_have_value('確認無誤，歸檔')
        self.click('#finalize-form button')
        self.step('完成')

    def test_native_dialog_keyboard_cancel_and_custom_filename(self):
        p = self.page
        p.evaluate("m.step=3;m.backstage='open';render()")
        self.native('browse')
        p.locator('[data-native="pick-xml"]').focus()
        p.keyboard.press('Enter')
        expect(p.locator('#mn-dialog-title')).to_have_text('開啟 XML')
        p.keyboard.press('Escape')
        expect(p.locator('[data-native="pick-xml"]')).to_be_focused()
        p.keyboard.press('Enter')
        p.keyboard.press('Enter')
        self.step('檢視資料並另存')
        p.locator('[data-native="backstage"]').press('Control+Shift+s')
        p.locator('#mn-filename').fill('bad/name')
        self.native('save-workbook')
        expect(p.locator('#mn-error')).to_contain_text('有效')
        p.locator('#mn-filename').fill('11507_練習.XLSX')
        p.keyboard.press('Escape')
        self.native('browse')
        expect(p.locator('#mn-filename')).to_have_value('11507_練習.XLSX')
        p.locator('#mn-filename').press('Enter')
        self.step('建立樞紐分析表')
        p.evaluate("m.step=8;m.manualLocation='documents';render()")
        p.locator('[data-file="11507_練習.XLSX"]').dblclick()
        expect(p.locator('.window-name')).to_contain_text('11507_練習.XLSX')
        self.native('return-explorer')
        expect(p.locator('.mn-explorer')).to_be_visible()

    def test_outer_page_navigation_reset_and_focus(self):
        for width in [1440, 768, 390, 320]:
            with self.subTest(width=width):
                p = self.new_page(width, 800)
                p.keyboard.press('Tab')
                expect(p.locator('.skip-link')).to_be_focused()
                p.keyboard.press('Enter')
                expect(p.locator('#experience')).to_be_focused()
                self.click('.intro-link')
                expect(p.locator('#tab-original')).to_be_focused()
                p.keyboard.press('End')
                expect(p.locator('#tab-skill')).to_be_focused()
                p.keyboard.press('Home')
                p.keyboard.press('ArrowRight')
                expect(p.locator('#tab-skill')).to_have_attribute('aria-selected', 'true')
                p.keyboard.press('ArrowLeft')
                self.click('.workspace-jump')
                expect(p.locator('#experience')).to_be_focused()
                self.action('login')
                self.click('.workspace-mode[data-mode="skill"]')
                self.click('.workspace-mode[data-mode="original"]')
                self.step('匯出照會資料')
                expect(p.locator('#workspace-step-label')).to_have_text('步驟 02 / 09')
                p.once('dialog', lambda dialog: dialog.dismiss())
                self.click('#reset')
                self.step('匯出照會資料')
                self.click('#focus-toggle')
                expect(p.locator('.intro')).to_be_hidden()
                expect(p.locator('#sidebar')).to_be_hidden()
                expect(p.locator('.workspace-mode[data-mode="skill"]')).to_be_visible()
                p.locator('#experience').focus()
                p.keyboard.press('Escape')
                expect(p.locator('.intro')).to_be_visible()
                p.once('dialog', lambda dialog: dialog.accept())
                self.click('#reset')
                self.step('登入照管平台')
                self.assertTrue(p.evaluate('document.documentElement.scrollWidth<=innerWidth'))

    def test_fullscreen_tooltips_and_reduced_motion(self):
        p = self.page
        p.locator('#reset').focus()
        expect(p.locator('#reset-tip')).to_be_visible()
        p.keyboard.press('Escape')
        expect(p.locator('#reset-tip')).to_be_hidden()
        self.click('#fullscreen')
        self.assertTrue(p.evaluate('!!document.fullscreenElement'))
        expect(p.locator('#fullscreen')).to_have_attribute('aria-pressed', 'true')
        self.click('#fullscreen')
        self.assertFalse(p.evaluate('!!document.fullscreenElement'))
        p.evaluate("()=>{document.documentElement.requestFullscreen=()=>Promise.reject(new Error('test denial'))}")
        self.click('#fullscreen')
        expect(p.locator('#shell-status')).to_contain_text('未允許全螢幕')
        self.assertEqual('none', p.locator('.intro-copy').evaluate('e=>getComputedStyle(e).animationName'))
        self.assertEqual('0s', p.locator('#reset .lab-icon').evaluate('e=>getComputedStyle(e).transitionDuration'))

    def test_explorer_history_context_menu_drag_and_taskbar(self):
        p = self.page
        self.click('#tab-skill')
        p.locator('#download-xml').click(button='right')
        self.click('#wx-context [data-explorer="cut"]')
        self.click('[data-explorer="go-agent"]')
        p.locator('.wx-folder-item').dblclick()
        p.locator('#wx-files').focus()
        p.keyboard.press('Control+v')
        expect(p.locator('#input-xml')).to_be_visible()
        self.click('[data-explorer="back"]')
        expect(p.locator('.wx-folder-item')).to_be_visible()
        self.click('[data-explorer="forward"]')
        expect(p.locator('#input-xml')).to_be_visible()
        p.locator('#wx-files').focus()
        p.keyboard.press('Control+z')
        expect(p.locator('#download-xml')).to_be_visible()
        expect(p.locator('[data-action="place-xml"]')).to_be_disabled()
        p.locator('#wx-search').fill('not-found')
        expect(p.locator('.wx-empty')).to_contain_text('找不到')
        p.locator('#wx-search').fill('')
        p.locator('#download-xml').drag_to(p.locator('#input-drop'))
        expect(p.locator('#input-xml')).to_be_visible()
        self.click('[data-window="minimize"]')
        self.action('place-xml')
        expect(p.locator('#command')).to_be_focused()
        expect(p.locator('#stage')).to_be_visible()

    def test_window_restore_and_review_dialog_focus(self):
        p = self.page
        for mode, step in [('original', 2), ('original', 3), ('skill', 0), ('skill', 2)]:
            p.evaluate(f"mode='{mode}';{'m' if mode=='original' else 's'}.step={step};render()")
            self.click('[data-window="minimize"]')
            expect(p.locator('#stage')).to_be_hidden()
            self.click('.window-resting [data-window="restore"]')
            expect(p.locator('#stage')).to_be_visible()
            self.click('[data-window="close"]')
            self.click('.window-resting [data-window="restore"]')
            expect(p.locator('#stage')).to_be_visible()
        p.evaluate("s.step=3;s.choice='ignore';render()")
        self.action('review')
        self.assertTrue(p.locator('main').evaluate('e=>e.inert'))
        p.keyboard.press('Shift+Tab')
        expect(p.locator('[data-action="review-done"]')).to_be_focused()
        p.keyboard.press('Tab')
        expect(p.locator('[data-action="close-review"]')).to_be_focused()
        p.keyboard.press('Escape')
        expect(p.locator('[data-action="review"]')).to_be_focused()
        self.assertFalse(p.locator('main').evaluate('e=>e.inert'))


if __name__ == '__main__':
    unittest.main()
