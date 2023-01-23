import networkx as nx
import matplotlib.pyplot as plt
import math
import itertools
from itertools import count
import collections


class network_eda:
    def __init__(self, df):
        self.df = df
        self.G = None

    def user_graph(self):
        self.G = nx.from_pandas_edgelist(self.df, source="username",
                                         target='reply_to_user.username')

    def user_graph_directed(self):
        self.G = nx.from_pandas_edgelist(self.df, source="username",
                                         target='reply_to_user.username',
                                         create_using=nx.DiGraph())

    def user_post_graph(self):
        self.G = nx.Graph()
        self.G.add_nodes_from([node for node in self.df.username])
        for ie in set(self.df['topic_id']):
            indices = self.df[self.df['topic_id'] == ie].username
            self.G.add_edges_from(itertools.product(indices, indices))

    def add_trust_level(self):
        trust_dict = self.df.groupby("username")['trust_level'].mean().to_dict()
        # if user based graph
        nx.set_node_attributes(self.G, trust_dict, name='trust_level')

    def remove_selfloops(self):
        self.G.remove_edges_from(nx.selfloop_edges(self.G))

    def remove_isolated_nodes(self):
        self.G.remove_nodes_from(list(nx.isolates(self.G)))

    def remove_nan_nodes(self):
        nan_nodes = []
        for node in self.G.nodes():
            if type(node) is str:
                pass
            else:

                if math.isnan(node):
                    nan_nodes.append(node)

        self.G.remove_nodes_from(nan_nodes)

    def group_graph_plot(self, color=None):
        # select largest connected component
        cc_max = max(nx.connected_components(self.G), key=len)
        sub = self.G.subgraph(cc_max)
        groups = set(nx.get_node_attributes(sub, color).values())
        mapping = dict(zip(sorted(groups), count()))
        nodes = sub.nodes()
        colors = [mapping[sub.nodes[n][color]] for n in nodes]
        plt.figure(figsize=(15, 10))
        pos = nx.spring_layout(sub)
        nc = nx.draw_networkx_nodes(sub, pos, node_size=50, node_color=colors, cmap="tab20b", label=colors)
        nx.draw_networkx_edges(sub, pos, alpha=0.4)
        plt.colorbar(nc)

    def degree_histogram(self):
        degree_sequence = sorted([d for n, d in self.G.degree()], reverse=True)  # degree sequence

        degreeCount = collections.Counter(degree_sequence)
        deg, cnt = zip(*degreeCount.items())

        fig, ax = plt.subplots()
        plt.bar(deg, cnt, width=0.80, color='b')

        plt.title("Degree Histogram")
        plt.ylabel("Count")
        plt.xlabel("Degree")

    @staticmethod
    def sort_dict(in_dict):
        return {k: v for k, v in sorted(in_dict.items(), key=lambda item: item[1], reverse=True)}

    def get_graph(self):
        return (self.G)