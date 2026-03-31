from src.rpa.base import WebAutomator


class FormFiller(WebAutomator):
    def fill_form(self, url: str, fields: dict, submit_selector: str | None = None):
        self.go(url)
        for selector, value in fields.items():
            self.type_into(selector, value)
        if submit_selector:
            self.click(submit_selector)
        return True
