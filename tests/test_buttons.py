"""Every rendered demo button is classified and its result asserted.
Background controls covered by a dialog/menu are tested in their unobstructed state.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import expect
from test_workflow import BrowserTestCase


STATES = [(f'manual-{i+1}', f"m.step={i};" + ("m.manualLocation='documents';" if i == 8 else '')) for i in range(9)]
STATES += [(f'skill-{i+1}', f"mode='skill';s.step={i};s.choice='add';") for i in range(5)]
STATES += [
    ('manual-export-ready', 'm.step=1;m.queried=true;'),
    ('manual-start', 'm.step=2;m.startOpen=true;'),
    ('manual-history-back', "m.step=2;m.manualLocation='documents';m.manualHistory=['downloads','documents'];m.manualHistoryIndex=1;"),
    ('manual-history-forward', "m.step=2;m.manualHistory=['downloads','documents'];m.manualHistoryIndex=0;"),
    ('excel-home', "m.step=3;m.backstage='home';"),
    ('excel-open', "m.step=3;m.backstage='open';"),
    ('xml-picker', "m.step=3;m.backstage='open';m.nativeDialog='open';"),
    ('xml-picker-selected', "m.step=3;m.backstage='open';m.nativeDialog='open';m.openName='11507_demo.xml';"),
    ('xml-options', "m.step=3;m.nativeDialog='xml';"),
    ('xml-readonly', "m.step=3;m.nativeDialog='xml';m.xmlMode='readonly';"),
    ('xml-source', "m.step=3;m.nativeDialog='xml';m.xmlMode='source';"),
    ('excel-loaded-home', "m.step=4;m.backstage='home';"),
    ('save-page', "m.step=4;m.backstage='save';"),
    ('save-dialog', "m.step=4;m.backstage='save';m.nativeDialog='save';m.dialogLocation='documents';"),
    ('save-dialog-wrong-type', "m.step=4;m.backstage='save';m.nativeDialog='save';m.saveType='xml';"),
    ('pivot-ready', "m.step=5;m.fields=['PIB_UNIT','CASENO','SERVICE_CODE','ACCEPT'];"),
    ('report-empty', "m.step=6;m.workbook='report';"),
    ('report-ready', "m.step=6;m.workbook='report';m.seen=new Set(['BA','BB','DA']);m.values=[[14,11],[10,8],[8,6],[12,9]].map(a=>a.map(String));"),
    ('manual-review-ready', 'm.step=7;m.reviewChecks=[true,true,true];'),
    ('saved-report-preview', "m.step=8;m.completedPreview='report';"),
    ('saved-data-preview', "m.step=8;m.completedPreview='raw';"),
    ('skill-selected', "mode='skill';s.selected=true;"),
    ('skill-agent', "mode='skill';s.location='agent';s.fileHistory=['downloads','agent'];s.fileHistoryIndex=1;"),
    ('skill-history-forward', "mode='skill';s.fileHistory=['downloads','agent'];"),
    ('skill-paste-ready', "mode='skill';s.location='input';s.cut=true;s.fileHistory=['downloads','agent','input'];s.fileHistoryIndex=2;"),
    ('skill-moved', "mode='skill';s.location='input';s.moved=true;s.selected=true;s.fileHistory=['downloads','agent','input'];s.fileHistoryIndex=2;"),
    ('skill-suggestions', "mode='skill';s.step=1;s.command='/sas';"),
    ('skill-selected-command', "mode='skill';s.step=1;s.skillChosen=true;"),
    ('skill-run-ready', "mode='skill';s.step=1;s.skillChosen=true;s.command='執行';"),
    ('skill-add-ready', "mode='skill';s.step=2;s.unitReply='1 加入';"),
    ('skill-ignore-ready', "mode='skill';s.step=2;s.unitReply='全部忽略';"),
    ('skill-archive-invalid', "mode='skill';s.step=3;s.choice='ignore';s.reviewed=true;s.reviewChecks=[true,true,true];s.confirmation='尚未確認';"),
    ('skill-archive-ready', "mode='skill';s.step=3;s.choice='add';s.reviewed=true;s.reviewChecks=[true,true,true];s.confirmation='確認無誤，歸檔';"),
    ('skill-review', "mode='skill';s.step=3;s.choice='add';"),
    ('skill-review-ready', "mode='skill';s.step=3;s.choice='ignore';s.reviewChecks=[true,true,true];"),
    ('context-file', "mode='skill';s.selected=true;"),
    ('context-folder', "mode='skill';s.location='agent';s.selected=true;"),
    ('context-paste', "mode='skill';s.location='input';s.cut=true;"),
    ('context-undo', "mode='skill';s.location='input';s.moved=true;"),
]
SCOPE = '.window button,.mn-completion button,#review button'


class ButtonAudit(BrowserTestCase):
    def prepare(self, name, state):
        self.page.evaluate("closeReview(false);labLastMode=null;labLastStep=-1;mode='original';m=newManual();s=newSkill();" + state + 'render()')
        if name.startswith('skill-review'):
            self.action('review')
        if name.startswith('context-'):
            self.page.locator('#wx-files').click(button='right', position={'x': 35, 'y': 80}) if name in ['context-paste', 'context-undo'] else self.page.locator('.wx-item').click(button='right')

    def buttons(self):
        return self.page.locator(SCOPE).evaluate_all("""els=>els.map((e,index)=>({
            index, visible:e.checkVisibility(), name:e.getAttribute('aria-label')||e.textContent.trim(),
            action:e.dataset.action, native:e.dataset.native, explorer:e.dataset.explorer,
            window:e.dataset.window, page:e.dataset.page, location:e.dataset.location,
            file:e.dataset.file, form:e.closest('form')?.id,
            disabled:e.disabled||e.getAttribute('aria-disabled')==='true',
            background:!!e.closest('[inert]')||(!document.querySelector('#mn-start')?.hidden&&document.querySelector('#mn-start')&&!e.closest('#mn-start')&&e.closest('#stage'))||(!document.querySelector('#wx-context')?.hidden&&document.querySelector('#wx-context')&&!e.closest('#wx-context')&&e.closest('#stage'))
        })).filter(e=>e.visible)""")

    def test_every_rendered_button(self):
        records = []
        for width, height in [(1366, 768), (390, 664)]:
            self.new_page(width, height)
            for name, state in STATES:
                self.prepare(name, state)
                inventory = self.buttons()
                for button in inventory:
                    with self.subTest(width=width, state=name, button=button['name']):
                        self.prepare(name, state)
                        control = self.page.locator(SCOPE).nth(button['index'])
                        if button['background']:
                            records.append([width, name, button['name'], 'background; checked in unobstructed state'])
                            continue
                        if button['disabled']:
                            expect(control).to_be_disabled()
                            records.append([width, name, button['name'], 'disabled as expected'])
                            continue
                        before = self.page.evaluate("({mode,step:(mode==='original'?m:s).step,dialog:m.nativeDialog,backstage:m.backstage,location:s.location,cut:s.cut,moved:s.moved,manualLocation:m.manualLocation})")
                        control.click()
                        self.assert_effect(button, before, name)
                        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                        records.append([width, name, button['name'], 'clicked; expected result verified'])
        destination = os.environ.get('SAS_BUTTON_AUDIT_JSON')
        if destination:
            Path(destination).write_text(json.dumps(records, ensure_ascii=False, indent=2))

    def assert_effect(self, b, before, scenario):
        p = self.page
        if b.get('window'):
            if b['window'] == 'maximize':
                self.assertTrue(p.locator('.window').evaluate("e=>e.classList.contains('is-maximized')"))
                self.click('[data-window="maximize"]')
                self.assertFalse(p.locator('.window').evaluate("e=>e.classList.contains('is-maximized')"))
            elif b['window'] in ['close', 'minimize']:
                expect(p.locator('#stage')).to_be_hidden()
                self.click('.window-resting [data-window="restore"]')
                expect(p.locator('#stage')).to_be_visible()
            else:
                expect(p.locator('#stage')).to_be_visible()
            self.assertEqual(before['step'], p.evaluate("(mode==='original'?m:s).step"))
            return
        action = b.get('action')
        if action:
            if action in ['login', 'export', 'create-pivot', 'fill-report', 'save-report']:
                advances = action in ['login', 'export'] or scenario in ['pivot-ready', 'report-ready', 'manual-review-ready']
                self.assertEqual(before['step'] + int(advances), p.evaluate('m.step'))
                if not advances:
                    self.assertTrue(p.locator('#error').inner_text().strip())
            elif action == 'query':
                expect(p.locator('[data-action="export"]')).to_be_visible()
            elif action in ['show-pivot', 'show-report']:
                expect(p.locator('.pivot-layout' if action == 'show-pivot' else '#assigned-0')).to_be_visible()
            elif action in ['switch-skill', 'switch-original']:
                self.assertEqual('skill' if action == 'switch-skill' else 'original', p.evaluate('mode'))
            elif action == 'place-xml':
                expect(p.locator('#command')).to_be_focused()
                self.assertEqual(1, p.evaluate('s.step'))
            elif action == 'select-sas':
                expect(p.locator('#chosen-skill')).to_be_visible()
                expect(p.locator('#command')).to_have_value('')
            elif action == 'clear-sas':
                expect(p.locator('#chosen-skill')).to_be_hidden()
            elif action == 'review':
                expect(p.locator('#review')).to_be_visible()
            elif action == 'close-review':
                expect(p.locator('#review')).to_be_hidden()
            elif action == 'review-done':
                if scenario == 'skill-review-ready':
                    expect(p.locator('#review')).to_be_hidden()
                    expect(p.locator('#confirmation')).to_be_enabled()
                else:
                    expect(p.locator('#review-error')).to_contain_text('三項')
            else:
                self.fail(f'Uncovered action: {action}')
            return
        native = b.get('native')
        if native:
            if native == 'start':
                expect(p.locator('#mn-start')).to_be_hidden() if scenario == 'manual-start' else expect(p.locator('#mn-start')).to_be_visible()
            elif native == 'close-start':
                expect(p.locator('#mn-start')).to_be_hidden()
            elif native == 'launch-excel':
                self.step('以 XML 表格匯入')
                expect(p.locator('.mn-backstage')).to_be_visible()
            elif native in ['folder', 'explorer-back', 'explorer-forward']:
                target = b.get('location') or ('documents' if native == 'explorer-forward' else 'downloads')
                expect(p.locator('.mn-explorer .wx-address')).to_contain_text('文件' if target == 'documents' else '下載')
            elif native == 'select-file':
                expect(p.locator('.mn-explorer .wx-item[aria-pressed="true"]')).to_have_count(1)
            elif native == 'return-explorer':
                expect(p.locator('.mn-explorer')).to_be_visible()
            elif native == 'backstage':
                expect(p.locator('[data-page="home"]')).to_have_attribute('aria-current', 'page')
            elif native == 'backstage-page':
                expect(p.locator(f'[data-page="{b["page"]}"]')).to_have_attribute('aria-current', 'page')
            elif native == 'back-workbook':
                expect(p.locator('.raw-grid' if before['step'] == 4 else '.mn-blank')).to_be_visible()
            elif native == 'browse':
                expect(p.locator('#mn-dialog-title')).to_have_text('另存新檔' if before['backstage'] == 'save' else '開啟')
            elif native == 'dialog-folder':
                expect(p.locator('#mn-dialog .wx-address')).to_contain_text('文件' if b['location'] == 'documents' else '下載')
            elif native == 'pick-xml':
                expect(p.locator('#mn-filename')).to_have_value('11507_demo.xml')
            elif native == 'open-xml':
                if scenario == 'xml-picker-selected':
                    expect(p.locator('#mn-dialog-title')).to_have_text('開啟 XML')
                else:
                    expect(p.locator('#mn-error')).to_contain_text('找不到')
            elif native == 'cancel-dialog':
                if before['dialog'] == 'xml':
                    expect(p.locator('#mn-dialog-title')).to_have_text('開啟')
                else:
                    expect(p.locator('#mn-dialog')).to_have_count(0)
            elif native == 'import-xml':
                if scenario == 'xml-options':
                    self.step('檢視資料並另存')
                else:
                    expect(p.locator('#mn-error')).to_contain_text('XML 表格')
            elif native == 'save-workbook':
                if scenario == 'save-dialog':
                    self.step('建立樞紐分析表')
                else:
                    expect(p.locator('#mn-error')).to_contain_text('Excel 活頁簿')
            else:
                self.fail(f'Uncovered native action: {native}')
            return
        explorer = b.get('explorer')
        if explorer:
            target = None
            if explorer.startswith('go-'):
                target = explorer[3:]
            elif explorer in ['back', 'undo']:
                target = 'downloads' if explorer == 'undo' or scenario == 'skill-agent' else 'agent'
            elif explorer in ['forward', 'up', 'open-folder']:
                target = 'input' if explorer == 'open-folder' else 'agent'
            if target:
                self.assertEqual(target, p.evaluate('s.location'))
            elif explorer in ['select-file', 'select-folder']:
                expect(p.locator('.wx-item')).to_have_attribute('aria-pressed', 'true')
            elif explorer == 'cut':
                expect(p.locator('#download-xml')).to_have_class('wx-item is-cut')
            elif explorer == 'paste':
                expect(p.locator('#input-xml')).to_be_visible()
                expect(p.locator('[data-action="place-xml"]')).to_be_enabled()
            else:
                self.fail(f'Uncovered explorer action: {explorer}')
            return
        if b.get('form') == 'run-form':
            self.step('決定新單位')
        elif b.get('form') == 'unit-reply-form':
            if scenario in ['skill-add-ready', 'skill-ignore-ready']:
                self.step('Excel 檢核與歸檔')
            else:
                expect(p.locator('#unit-reply-error')).to_contain_text('目前只有編號 1')
        elif b.get('form') == 'finalize-form':
            if scenario == 'skill-archive-ready':
                self.step('完成')
            else:
                expect(p.locator('#error')).to_contain_text('請明確輸入')
        else:
            self.fail(f'Enabled button without a tested effect: {b}')

    def test_manual_history_and_loaded_workbook(self):
        self.prepare('manual-3', 'm.step=2;')
        self.click('[data-native="folder"][data-location="documents"]')
        expect(self.page.locator('.mn-explorer .wx-statusbar')).to_contain_text('文件')
        self.native('explorer-back')
        expect(self.page.locator('[data-native="explorer-forward"]')).to_be_enabled()
        self.native('explorer-forward')
        expect(self.page.locator('.mn-explorer .wx-address')).to_contain_text('文件')
        self.native('explorer-back')
        self.click('[data-native="folder"][data-location="documents"]')
        expect(self.page.locator('[data-native="explorer-forward"]')).to_be_disabled()
        self.native('explorer-back')
        expect(self.page.locator('.mn-explorer .wx-statusbar')).to_contain_text('下載')
        expect(self.page.locator('[data-native="explorer-back"]')).to_be_disabled()
        self.prepare('excel-loaded-home', "m.step=4;m.backstage='home';")
        expect(self.page.locator('.mn-blank-tile')).to_be_disabled()
        self.click('[data-native="back-workbook"][aria-label]')
        expect(self.page.locator('.raw-grid')).to_be_visible()

    def test_pivot_fields_and_all_filter_options(self):
        for bits in range(16):
            self.prepare('pivot', 'm.step=5;')
            for index, checkbox in enumerate(self.page.locator('[data-pivot-field]').all()):
                checkbox.set_checked(bool(bits & (1 << index)))
            self.action('create-pivot')
            self.assertEqual(6 if bits == 15 else 5, self.page.evaluate('m.step'))
        for code, assigned, accepted in [('BA', ['14','12'], ['11','9']), ('BB', ['10'], ['8']), ('DA', ['8'], ['6'])]:
            for option, expected in [('all', assigned), ('yes', accepted)]:
                self.page.locator('#code-filter').select_option(code)
                self.page.locator('#accept-filter').select_option(option)
                self.assertEqual(expected, self.page.locator('.pivot-group td:last-child').all_text_contents())

    def test_search_and_both_saved_workbook_previews(self):
        for width, height in [(1366, 768), (390, 664)]:
            self.new_page(width, height)
            self.prepare('manual-3', 'm.step=2;')
            self.page.locator('#mn-search').fill('missing.xml')
            expect(self.page.locator('.mn-explorer .wx-empty')).to_contain_text('找不到')
            self.page.locator('#mn-search').fill('DEMO.XML')
            expect(self.page.locator('[data-file="11507_demo.xml"]')).to_be_visible()
            self.native('start')
            self.page.locator('#mn-start-search').fill('missing app')
            expect(self.page.locator('#mn-start-empty')).to_be_visible()
            self.page.locator('#mn-start-search').fill('excel')
            expect(self.page.locator('[data-native="launch-excel"]')).to_be_visible()
            expect(self.page.locator('[data-native="close-start"]')).to_be_hidden()
            self.page.locator('#mn-start-search').press('Enter')
            self.step('以 XML 表格匯入')
            for filename, selector in [('11507_輪派報表.xlsx', 'table.report'),
                                       ('11507_照會資料.xlsx', '.raw-grid')]:
                for gesture in ['double-click', 'Enter']:
                    self.prepare('saved', "m.step=8;m.manualLocation='documents';")
                    row = self.page.locator(f'[data-file="{filename}"]')
                    row.dblclick() if gesture == 'double-click' else row.press('Enter')
                    expect(self.page.locator('.window-name')).to_contain_text(filename)
                    expect(self.page.locator(selector)).to_be_visible()
                    self.native('return-explorer')
                    expect(self.page.locator('.mn-explorer')).to_be_visible()

    def test_all_checkboxes_and_detail_toggles(self):
        for bits in range(8):
            self.prepare('manual-8', 'm.step=7;')
            for index, checkbox in enumerate(self.page.locator('#stage .review-check').all()):
                checkbox.set_checked(bool(bits & (1 << index)))
            self.action('save-report')
            self.assertEqual(8 if bits == 7 else 7, self.page.evaluate('m.step'))
            self.prepare('skill-review', "mode='skill';s.step=3;s.choice='add';")
            for index, checkbox in enumerate(self.page.locator('#review .review-check').all()):
                checkbox.set_checked(bool(bits & (1 << index)))
            self.action('review-done')
            self.assertEqual(bits == 7, self.page.locator('#review').is_hidden())
        for step in [1, 2, 3, 4]:
            self.prepare('details', f"mode='skill';s.step={step};s.choice='add';")
            for detail in self.page.locator('#stage details').all():
                detail.locator('summary').click()
                expect(detail).to_have_attribute('open', '')
                detail.locator('summary').click()
                self.assertIsNone(detail.get_attribute('open'))
