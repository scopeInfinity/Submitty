import tempfile
import os
import urllib
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from .base_testcase import BaseTestCase

class TestForum(BaseTestCase):
    def __init__(self,testname):
        super().__init__(testname,user_id="instructor", user_password="instructor", user_name="Quinn")

    def init_and_enable_discussion(self):
        self.driver.find_element_by_id(self.get_current_semester() + '_sample').click()
        if len(self.driver.find_elements_by_xpath("//a[contains(string(),'Discussion Forum')]")) == 0:
            self.driver.find_element_by_xpath("//a[contains(text(),'Course Settings')]").click()
            self.driver.find_element_by_name("forum_enabled").click()
            self.driver.find_element_by_xpath("//button[@form = 'configForm']").click()
            self.driver.find_element_by_xpath("//a[contains(text(),'sample')]").click()
        self.driver.find_element_by_xpath("//a[contains(string(),'Discussion Forum')]").click()
        self.forum_page_url = self.driver.current_url

    def switch_to_page_create_thread(self):
        if 'page=create_thread' in self.driver.current_url:
            pass
        elif 'page=view_thread' in self.driver.current_url:
            self.driver.find_element_by_xpath("//a[contains(text(),'Create Thread')]").click()
        else:
            assert False
        assert 'page=create_thread' in self.driver.current_url

    def switch_to_page_view_thread(self):
        if 'page=view_thread' in self.driver.current_url:
            pass
        elif 'page=create_thread' in self.driver.current_url:
            self.driver.find_element_by_xpath("//a[contains(text(),'Back to Threads')]").click()
        else:
            assert False
        assert 'page=view_thread' in self.driver.current_url

    def upload_attachment(self, upload_button):
        tfname = self.create_dummy_file()
        upload_button.send_keys(tfname)
        return os.path.basename(tfname)

    def select_categories(self, categories_list):
        assert 'page=create_thread' in self.driver.current_url
        for category, set_it in categories_list:
            category_button = self.driver.find_element_by_xpath("//a[contains(@class,'cat-buttons') and contains(string(),'{}')]".format(category))
            if ('cat-selected' in category_button.get_attribute('class')) ^ set_it:
                category_button.click()

    def create_thread(self, title, first_post, ignore_if_exists = False, upload_attachment = False, categories_list = [("Question",True)]):
        assert 'page=view_thread' in self.driver.current_url
        if ignore_if_exists and self.thread_exists(title):
            return
        attachment_file = None
        self.switch_to_page_create_thread()
        self.driver.find_element_by_id("title").send_keys(title)
        self.driver.find_element_by_id("thread_post_content").send_keys(first_post)
        upload_button = self.driver.find_element_by_xpath("//input[@type='file']")
        self.select_categories(categories_list)
        if upload_attachment:
            attachment_file = self.upload_attachment(upload_button)
        self.driver.find_element_by_xpath("//input[@value='Submit Post']").click()
        if len([cat for cat in categories_list if cat[1]]) == 0:
            # Test thread should not be created
            self.driver.switch_to.alert.accept();
            self.switch_to_page_view_thread()
            assert not self.thread_exists(title)
            return None
        self.wait_after_ajax()
        assert 'page=view_thread' in self.driver.current_url
        return attachment_file

    def thread_exists(self, title):
        assert 'page=view_thread' in self.driver.current_url
        target_xpath = "//div[contains(@class, 'thread_box') and contains(string(),'{}')]".format(title)
        loading_spinner = self.driver.find_element_by_xpath("//div[@id='thread_list']/i");
        while True:
            # Scroll down in thread list until required thread is found
            divs = self.driver.find_elements_by_xpath(target_xpath)
            if len(divs) > 0:
                # Thread Found
                break
            thread_list = self.driver.find_element_by_id("thread_list")
            # Scroll Dowm
            self.driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', thread_list)
            if not loading_spinner.is_displayed():
                break
            self.wait_after_ajax()
            assert not loading_spinner.is_displayed()
        return len(self.driver.find_elements_by_xpath(target_xpath)) > 0

    def view_thread(self, title, return_info = False):
        assert 'page=view_thread' in self.driver.current_url
        self.thread_exists(title)
        div = self.driver.find_element_by_xpath("//div[contains(@class, 'thread_box') and contains(string(),'{}')]".format(title))
        if return_info:
            categories = []
            for element in div.find_elements(By.XPATH, ".//span[contains(@class, 'label_forum')]"):
                categories.append(element.text.strip())
            return {'categories': categories}
        div.click()
        thread_title = self.driver.find_elements_by_xpath("//div[contains(@class, 'post_box') and contains(@class, 'first_post')]/h3[contains(string(),'{}')]".format(title))
        assert len(thread_title) > 0
        assert thread_title[0].text.strip() == title.strip()

    def find_posts(self, content, must_exists = True, move_to_thread = None, check_attachment = None):
        if move_to_thread is not None:
            self.view_thread(move_to_thread)
        posts = self.driver.find_elements_by_xpath("//div[contains(@class, 'post_box') and contains(string(),'{}')]".format(content))
        if must_exists:
            assert len(posts) > 0
        if check_attachment is not None:
            assert len(posts[0].find_elements(By.XPATH, ".//a[contains(normalize-space(.), '{}')]".format(check_attachment))) > 0
        return posts

    def reply_and_test(self, post_content, newcontent, first_post, upload_attachment = False):
        attachment_file = None
        post = self.find_posts(post_content)[0]
        post_id = post.get_attribute("id")
        edit_form = self.driver.find_elements_by_xpath("//input[@value='{}' and @name='parent_id']/..".format(post_id))[-1] #Last One
        text_area = edit_form.find_element(By.XPATH, ".//textarea")
        upload_button = edit_form.find_element(By.XPATH, ".//input[@type='file']")
        submit_button = edit_form.find_element(By.XPATH, ".//input[@type='submit']")
        if first_post:
            assert "first_post" in post.get_attribute("class")
        else:
            assert "first_post" not in post.get_attribute("class")
        if not text_area.is_displayed():
            post.find_element(By.XPATH, ".//a[contains(normalize-space(.), 'Reply')]").click()
        assert text_area.is_displayed()
        text_area.send_keys(newcontent)
        if upload_attachment:
            attachment_file = self.upload_attachment(upload_button)
        submit_button.click()
        print("INFO")
        print(post_content)
        print(newcontent)
        print(first_post)
        print(upload_attachment)
        
        print("Before Wait")
        print(submit_button)
        print(submit_button.get_attribute('innerHTML'))
        print(text_area)
        print(text_area.get_attribute('innerHTML'))
        print(text_area.get_attribute('value'))
        self.wait_after_ajax()
        self.driver.implicitly_wait(30)
        print("After Wait")
        print(submit_button)
        print(submit_button.get_attribute('innerHTML'))
        print(text_area)
        print(text_area.get_attribute('innerHTML'))
        print(text_area.get_attribute('value'))

        # Test existence only
        self.find_posts(newcontent, must_exists = True, check_attachment = attachment_file)
        return attachment_file

    def delete_thread(self, title):
        self.view_thread(title)
        self.driver.find_elements_by_xpath("//a[@title='Remove post']")[0].click()
        self.driver.switch_to.alert.accept();
        # Workaround, not working without force redirection
        self.driver.get(self.forum_page_url)

    def create_dummy_file(self):
        # Download image to create dummy image file
        tf = tempfile.NamedTemporaryFile().name + ".png"
        image_url = self.test_url + "/img/submitty_logo.png"
        urllib.request.urlretrieve(image_url, tf)
        return tf

    def merge_threads(self, child_thread_title, parent_thread_title, press_cancel = False):
        self.view_thread(child_thread_title)
        merge_threads_div = self.driver.find_element_by_id("merge-threads")
        self.driver.find_element_by_xpath("//a[contains(text(),'Merge Threads')]").click()
        self.wait_after_ajax()
        cancel_button = merge_threads_div.find_element(By.XPATH, ".//a[contains(normalize-space(.), 'Close')]")
        assert merge_threads_div.value_of_css_property("display") == "block"
        if parent_thread_title is None:
            cancel_button.click()
            assert merge_threads_div.value_of_css_property("display") == "none"
        else:
            submit_button = merge_threads_div.find_element(By.XPATH, ".//input[@value='Submit']")
            possible_parents = self.driver.find_element_by_name("merge_thread_parent")
            possible_parents.find_element(By.XPATH, ".//option[contains(normalize-space(.), '{}')]".format(parent_thread_title)).click()
            if press_cancel:
                cancel_button.click()
            else:
                submit_button.click()
            assert self.driver.find_element_by_id("merge-threads").value_of_css_property("display") == "none"

    def test_basic_operations_thread(self):
        title = "E2E Sample Title E2E"
        content = "E2E Sample Content E2E"
        reply_content1 = "E2E sample reply 1 content E2E"
        reply_content2 = "E2E sample reply 2 content E2E"
        reply_content3 = "E2E sample reply 3 content E2E"

        self.init_and_enable_discussion()
        for upload_attachment in [False, True]:
            assert not self.thread_exists(title)
            attachment = self.create_thread(title, content, upload_attachment = upload_attachment)

            self.find_posts(content, must_exists = True, check_attachment = attachment)
            self.view_thread(title)
            self.find_posts(content, must_exists = True)
            self.reply_and_test(content, reply_content1, first_post = True, upload_attachment = upload_attachment)
            self.reply_and_test(reply_content1, reply_content2, first_post = False)
            self.reply_and_test(reply_content2, reply_content3, first_post = False, upload_attachment = upload_attachment)

            assert self.thread_exists(title)
            self.delete_thread(title)
            assert not self.thread_exists(title)

    def test_forum_merge_thread(self):
        self.init_and_enable_discussion()
        title1 = "E2E Test 1 E2E"
        title2 = "E2E Test 2 E2E"
        title3 = "E2E Test 3 E2E"
        content1 = "E2E Content 1 E2E"
        content2 = "E2E Content 2 E2E"
        content3 = "E2E Content 3 E2E"

        reply1 = "E2E Reply 1 E2E"
        reply2 = "E2E Reply 2 E2E"
        reply3 = "E2E Reply 3 E2E"

        content1_attachment = self.create_thread(title1, content1, upload_attachment = True)
        self.reply_and_test(content1, reply1, first_post = True)
        self.create_thread(title2, content2)
        reply2_attachment = self.reply_and_test(content2, reply2, first_post = True, upload_attachment = True)
        self.create_thread(title3, content3)
        self.reply_and_test(content3, reply3, first_post = True)

        # Not Merging
        self.merge_threads(title1, None)
        self.merge_threads(title2, title1, press_cancel = True)

        self.find_posts(content1, must_exists = True, move_to_thread = title1, check_attachment = content1_attachment)
        self.find_posts(reply1, must_exists = True, move_to_thread = title1)
        self.find_posts(reply2, must_exists = True, move_to_thread = title2, check_attachment = reply2_attachment)
        self.find_posts(reply3, must_exists = True, move_to_thread = title3)

        # Merging success
        self.merge_threads(title2, title1, press_cancel = False)

        self.find_posts(content1, must_exists = True, move_to_thread = title1, check_attachment = content1_attachment)
        self.find_posts(reply1, must_exists = True)
        self.find_posts(content2, must_exists = True)
        self.find_posts(reply2, must_exists = True, check_attachment = reply2_attachment)
        self.find_posts(content3, must_exists = True, move_to_thread = title3)
        self.find_posts(reply3, must_exists = True)
        assert not self.thread_exists(title2)

        # Cleanup
        self.delete_thread(title3)
        self.delete_thread(title1)

    def test_categories(self):
        title1 = "E2E Sample Title 1 E2E"
        content1 = "E2E Sample Content 1 E2E"
        title2 = "E2E Sample Title 2 E2E"
        content2 = "E2E Sample Content 2 E2E"
        title3 = "E2E Sample Title 3 E2E"
        content3 = "E2E Sample Content 3 E2E"

        self.init_and_enable_discussion()

        # Check multiple categories
        assert not self.thread_exists(title1)
        assert not self.thread_exists(title2)
        self.create_thread(title1, content1, categories_list = [('Question', True), ('Comment', False), ('Tutorials', True)])
        self.create_thread(title2, content2, categories_list = [('Question', False), ('Comment', True), ('Tutorials', False)])
        # Creation Failed
        self.create_thread(title3, content3, categories_list = [('Question', False), ('Comment', False), ('Tutorials', False)])

        info1 = self.view_thread(title1, return_info = True)
        info2 = self.view_thread(title2, return_info = True)
        assert set(info1['categories']) == set(["Question", "Tutorials"])
        assert set(info2['categories']) == set(["Comment"])
        self.delete_thread(title1)
        self.delete_thread(title2)
        assert not self.thread_exists(title3)

    def test_infinite_scroll(self):
        self.init_and_enable_discussion()
        list_title = []
        list_content = []
        # Creation of 22 thread and then deleting them will be slow
        for i in range(0,22):
            list_title.append("E2E Sample Title {} E2E".format(i))
            list_content.append("E2E Sample Content {} E2E".format(i))

        # Create Threads
        for title,content in zip(list_title, list_content):
            assert not self.thread_exists(title)
            self.create_thread(title, content)

        # Check Threads
        for title in list_title:
            self.view_thread(title)
        self.view_thread(list_title[0])
        self.view_thread(list_title[-1])

        # Delete Threads
        for title in list_title:
            assert self.thread_exists(title)
            self.delete_thread(title)
            assert not self.thread_exists(title)

if __name__ == "__main__":
    import unittest
    unittest.main()
