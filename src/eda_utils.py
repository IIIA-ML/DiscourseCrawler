# import packages
import pandas as pd
import json
import networkx as nx
from sqlalchemy import create_engine
import matplotlib.pyplot as plt


class eda:
    # better way of doing it would be too loop flat json back to og df -> less modifications
    def __init__(self, db_link, table_name):
        self.engine = create_engine(db_link)
        with self.engine.connect() as connection:
            self.df = pd.read_sql_table(table_name, connection)

    # chec for jason
    def _decorator(foo):
        def check_for_json(self, left_col, right_col):
            if 'json' in self.df.columns:
                foo(self) # not best practice -> the whole decorator is stupid
                self.df = self.df.merge(self.json_df, how='left',
                                        left_on=left_col, right_on=right_col)
                # self.df = pd.concat([self.df, self.json_df], axis = 1)

        return check_for_json

    @_decorator
    def df_from_json(self):
        # Creates df from json
        json_list = []
        for item in self.df['json']:
            json_list.append(json.loads(item))
        self.json_df = pd.json_normalize(json_list)

    def get_like_column(self):
        like_list = []
        for item in self.df['actions_summary']:
            if len(item) == 0:
                like_list.append(0)
            else:
                # this is a bit stupid
                for element in item:
                    if element['id'] == 2:
                        like_list.append(element['count'])
        self.df['likes'] = like_list

    @staticmethod
    def bar_plot(values, plot_title, ignore_ticks=True):
        ax = values.plot(kind='bar')
        if ignore_ticks:
            ax.set_xticks([])
        ax.axhline(values.mean(), c='r')
        plt.text(0.5, .2, f"Mean: {values.mean().round(2)}", transform=ax.transAxes)
        plt.title(plot_title)

    # now eda part
    def show_cat_histogram(self, column, plot_title, ignore_ticks=True):
        values = self.df[column].value_counts()
        eda.bar_plot(values, plot_title, ignore_ticks)

    def groupby_histogram(self, group_by, column, plot_title):
        values = self.json_df.groupby(group_by)[column].sum()
        eda.bar_plot(values, plot_title)

    def return_json_df(self):
        return self.json_df

    def return_df(self):
        return self.df

    def overwrite_data(self, df):
        self.df = df