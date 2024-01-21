from datetime import datetime
from kivy.app import App
from kivy.properties import partial
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
import requests


class AirQualityApp(App):
    def build(self):
        self.title = 'Monitoring jakości powietrza'
        self.root = AirQualityLayout()
        return self.root


class AirQualityLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(AirQualityLayout, self).__init__(**kwargs)

        self.orientation = 'vertical'
        self.spacing = 5
        self.padding = [20, 20, 20, 20]

        self.text_input_style = {
            'background_color': (1, 1, 1, 1),
            'multiline': False,
            'font_size': '18sp',
            'padding': [10, 10],
            'size_hint_y': None,
            'height': '32sp',
            'border': (0, 20, 20, 20),
            'font_name': 'DejaVuSans'
        }

        self.label_style = {
            'font_size': '12sp',
            'color': (0.1, 0.7, 0.3, 1),
            'font_name': 'DejaVuSans'
        }

        self.convert_button_style = {
            'size_hint_y': None,
            'height': '32sp',
            'font_size': '14sp',
            'background_color': (0.1, 0.7, 0.3, 1),
            'padding': [10, 10],
            'font_name': 'DejaVuSans'
        }
        self.main_button_style = {
            'size_hint_y': None,
            'height': '50sp',
            'font_size': '14sp',
            'background_color': (0.1, 0.7, 0.3, 1),
            'padding': [10, 10],
            'font_name': 'DejaVuSans',
            'halign': 'center',
            'valign': 'middle'
        }
        self.selected_station_code = None

        self.result_label = Label(text='')
        self.city_input = TextInput(hint_text='Wprowadź nazwę miasta', **self.text_input_style)
        self.station_code_label = Label(text='Nie wybrano stacji', **self.label_style)

        header_label = Label(text='     Monitoring\njakości powietrza', font_size='24sp', color=(0.1, 0.7, 0.3, 1), )
        self.add_widget(header_label)
        self.add_widget(self.city_input)

        check_button = self.create_button('Sprawdź jakość powietrza', self.check_air_quality)
        self.add_widget(check_button)

        self.result_label = Label(text='Jakość powietrza: ', **self.label_style)
        self.add_widget(self.result_label)

        bottom_buttons_layout = GridLayout(cols=2, spacing=10, size_hint_y=None, height=100)
        history_button = Button(text='Poziom PM10 z\nostatnich\n'
                                     'trzech dni', on_press=self.show_historical_data, **self.main_button_style)
        stations_button = Button(text='Pokaż stacje', on_press=self.show_stations, **self.main_button_style)

        bottom_buttons_layout.add_widget(history_button)
        bottom_buttons_layout.add_widget(stations_button)
        self.add_widget(bottom_buttons_layout)

        self.blank_label = Label(text='')
        self.add_widget(self.blank_label)

        header_label = Label(text=' © Copyright 2023-2024 Julia Guzińska', font_size='10sp', color=(0.1, 0.7, 0.3, 1))
        self.add_widget(header_label)

    def create_button(self, text, on_press_handler):
        return Button(text=text, on_press=on_press_handler, **self.convert_button_style)

    def check_air_quality(self, instance):
        city_name = self.city_input.text.strip()

        if not city_name:
            self.result_label.text = 'Wpisz nazwę miasta.'
            return

        try:
            stations_data = self.get_stations_data()
            station_id = next((station['id'] for station in stations_data if city_name.lower() in
                               station['city']['name'].lower()), None)

            if station_id is not None:
                air_quality_data = self.get_air_quality_data(station_id)

                if 'stIndexLevel' in air_quality_data and 'indexLevelName' in air_quality_data['stIndexLevel']:
                    air_quality_index = air_quality_data['stIndexLevel']['indexLevelName']
                    self.result_label.text = f'Jakość powietrza w mieście {city_name}: {air_quality_index}'
                else:
                    self.result_label.text = f'Brak danych dla stacji {station_id} w mieście {city_name}.'
            else:
                self.result_label.text = f'Brak stacji w mieście {city_name}.'
        except requests.RequestException as e:
            self.result_label.text = f'Spróbuj ponownie'

    @staticmethod
    def get_stations_data():
        stations_url = f'http://api.gios.gov.pl/pjp-api/rest/station/findAll?size=500'
        stations_response = requests.get(stations_url)
        return stations_response.json()

    @staticmethod
    def get_air_quality_data(station_id):
        air_quality_url = f'http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/{station_id}'
        air_quality_response = requests.get(air_quality_url)
        return air_quality_response.json()

    def show_historical_data(self, instance):
        city_name = self.city_input.text.strip()

        if not city_name:
            self.result_label.text = 'Prosze wpisać miasto.'
            return

        try:
            stations_data = self.get_stations_data()

            city_stations = [station for station in stations_data
                             if city_name.lower() in station['city']['name'].lower()]

            if not city_stations:
                self.result_label.text = f'Brak stacji w mieście {city_name}.'
                return

            selected_station = city_stations[0]

            self.selected_station_code = selected_station['city']['commune']['districtName']
            self.station_code_label.text = f'Wybrana stacja: {self.selected_station_code}'

            historical_data = self.get_historical_data()
            grouped_data = self.group_historical_data(historical_data)

            history_popup = self.create_history_popup(grouped_data)
            history_popup.open()

        except requests.RequestException:
            self.result_label.text = 'Wystąpił błąd podczas pobierania danych, spróbuj ponownie.'

    @staticmethod
    def get_historical_data():
        historical_url = f'https://api.gios.gov.pl/pjp-api/v1/rest/aggregate/getAggregatePm10Data?size=500'
        historical_response = requests.get(historical_url)
        return historical_response.json().get("Lista danych zagregowanych", [])

    def group_historical_data(self, historical_data):
        grouped_data = {}
        for dat in historical_data:
            if dat['Powiat'] == self.selected_station_code:
                station_code = dat['Kod stanowiska']
                grouped_data.setdefault(station_code, []).append(
                    (datetime.strptime(dat['Data'], '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y'),
                     dat['Średnia 24-godzinna z wyników 1-godzinnych']))
        return grouped_data

    def create_history_popup(self, grouped_data):
        history_popup = Popup(title="Lista stacji", size_hint=(0.9, 0.5))
        popup_scroll_view = ScrollView(size_hint=(1, 1))
        inner_box_layout = BoxLayout(orientation='vertical', spacing=5)
        popup_scroll_view.add_widget(inner_box_layout)
        history_popup.content = popup_scroll_view

        for station_code, station_data in grouped_data.items():
            station_button = self.create_button(station_code, partial(self.show_current_stations, station_data))
            inner_box_layout.add_widget(station_button)

        return history_popup

    def show_current_stations(self, instance, arg):
        history_text = ''
        for entry in instance:
            try:
                history_text += f"Data: {entry[0]}, PM10: {entry[1]:.2f} ug/m3\n"
            except TypeError:
                history_text += f"Data: {entry[0]}, PM10: Brak danych\n"

        history_text += '\n'

        history_label = Label(text=history_text, **self.label_style)
        history_popup_content = BoxLayout(orientation='horizontal', spacing=5)
        history_popup_content.add_widget(history_label)
        history_popup = Popup(title='PM10', content=history_popup_content, size_hint=(0.7, 0.3))
        history_popup.open()

    def show_stations(self, instance):
        try:
            stations_data = self.get_stations_data()
            stations_list = [f"ID stacji: {station['id']}, "
                             f"Adres: {station['stationName']}" for station in stations_data if
                             station["city"]["name"] == self.city_input.text.strip().capitalize()]

            history_text = 'Stacje:\n' + '\n'.join(stations_list)

            history_label = Label(text=history_text, **self.label_style)
            history_popup_content = BoxLayout(orientation='vertical', spacing=5)
            history_popup_content.add_widget(history_label)
            history_popup = Popup(title='Lista stacji', content=history_popup_content, size_hint=(0.9, 0.5))
            history_popup.open()

        except requests.RequestException as e:
            self.result_label.text = f'Błąd: {str(e)}'


if __name__ == '__main__':
    AirQualityApp().run()

