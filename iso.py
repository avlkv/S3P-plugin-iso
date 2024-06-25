"""
Нагрузка плагина SPP

1/2 документ плагина
"""
import logging
import time
import dateparser
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from src.spp.types import SPP_document
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ISO:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'iso'
    _content_document: list[SPP_document]

    def __init__(self, webdriver: WebDriver, urls: tuple | list, last_document: SPP_document = None,
                 max_count_documents: int = 100, *args, **kwargs):
        """
        Конструктор класса парсера

        По умолчанию внего ничего не передается, но если требуется (например: driver селениума), то нужно будет
        заполнить конфигурацию
        """
        # Обнуление списка
        self._content_document = []

        self.driver = webdriver
        self.wait = WebDriverWait(self.driver, timeout=20)
        self.max_count_documents = max_count_documents
        self.last_document = last_document
        self.URLS = urls

        # Логер должен подключаться так. Вся настройка лежит на платформе
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Parser class init completed")
        self.logger.info(f"Set source: {self.SOURCE_NAME}")
        ...

    def content(self) -> list[SPP_document]:
        """
        Главный метод парсера. Его будет вызывать платформа. Он вызывает метод _parse и возвращает список документов
        :return:
        :rtype:
        """
        self.logger.debug("Parse process start")
        try:
            self._parse()
        except Exception as e:
            self.logger.debug(f'Parsing stopped with error: {e}')
        else:
            self.logger.debug("Parse process finished")
        return self._content_document

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter")

        for url in self.URLS:
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'tbody')))
            category = self.driver.find_element(By.CLASS_NAME, 'heading-condensed').text.replace('\n', ' ')
            docs = self.driver.find_elements(By.XPATH, "//tbody/tr[contains(@ng-show, 'pChecked')]")
            for doc in docs:
                title = doc.find_element(By.CLASS_NAME, 'clearfix').text.replace('\n', ' ')
                standard_link = (doc.find_element(By.CLASS_NAME, 'clearfix')
                                 .find_element(By.TAG_NAME, 'a').get_attribute('href'))
                stage_short = doc.find_element(By.XPATH, ".//td[contains(@data-title, 'Stage')]").text
                tech_committee_short = doc.find_element(By.XPATH, ".//td[contains(@data-title, 'TC')]").text

                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[1])

                self.driver.get(standard_link)
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'nav')))

                self.logger.debug(f'Enter {standard_link}')

                heading = self.driver.find_element(By.XPATH, "//nav[contains(@class, 'heading-condensed')]")

                # doc_ref = heading.find_element(By.TAG_NAME, 'h1').text
                # topic = heading.find_element(By.TAG_NAME, 'h2').text

                # try:
                #     subtopic = heading.find_element(By.TAG_NAME, 'h3').text
                # except:
                #     subtopic = None

                # try:
                #     part = heading.find_element(By.TAG_NAME, 'h4').text
                # except:
                #     part = None

                try:
                    abstract = self.driver.find_element(By.XPATH, "//div[contains(@itemprop,'description')]").text
                except:
                    abstract = None

                try:
                    status = self.driver.find_element(By.XPATH, "//a[contains(@title,'Life cycle')]").text
                except:
                    status = None

                pub_date = dateparser.parse(self.driver.find_element(
                    By.XPATH, "//div[@id = 'publicationDate']/span").text)

                web_link = self.driver.find_element(By.XPATH, "//a[contains(text(),'Read sample')]").get_attribute(
                    'href')

                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[2])

                self.driver.get(web_link)
                self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'sts-standard')))

                text_content = self.driver.find_element(By.XPATH, "//div[contains(@class, 'sts-standard')]").text

                other_data = {
                    # 'doc_ref': doc_ref,
                    # 'topic': topic,
                    # 'subtopic': subtopic,
                    # 'part': part,
                    'category' : category,
                    'category_link' : url,
                    'status': status,
                    'stage': stage_short,
                    'tech_committee': tech_committee_short,
                    'standard_page': standard_link
                }

                doc = SPP_document(
                    doc_id=None,
                    title=title,
                    abstract=abstract,
                    text=text_content,
                    web_link=web_link,
                    local_link=None,
                    other_data=other_data,
                    pub_date=pub_date,
                    load_date=datetime.now(),
                )

                self.find_document(doc)

                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

        # ---
        # ========================================
        ...

    def _find_document_text_for_logger(self, doc: SPP_document):
        """
        Единый для всех парсеров метод, который подготовит на основе SPP_document строку для логера
        :param doc: Документ, полученный парсером во время своей работы
        :type doc:
        :return: Строка для логера на основе документа
        :rtype:
        """
        return f"Find document | name: {doc.title} | link to web: {doc.web_link} | publication date: {doc.pub_date}"

    def find_document(self, _doc: SPP_document):
        """
        Метод для обработки найденного документа источника
        """
        if self.last_document and self.last_document.hash == _doc.hash:
            raise Exception(f"Find already existing document ({self.last_document})")

        if self.max_count_documents and len(self._content_document) >= self.max_count_documents:
            raise Exception(f"Max count articles reached ({self.max_count_documents})")

        self._content_document.append(_doc)
        self.logger.info(self._find_document_text_for_logger(_doc))
