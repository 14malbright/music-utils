# -*- coding: utf-8 -*-
from itertools import combinations
import os
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
import networkx as nx
from artist import Artist


def expand(artists, graph=None) -> nx.Graph:
    """
    Adds each artists' related artists to graph.

    Args:
        artists: An iterable of Artist objects or strings of artist IDs.
        graph: Optional; A networkx.Graph instance. graph is copied and not
            modified in-place. If graph is None, an empty graph is used.

    Returns:
        A networkx.Graph instance with Artist objects as nodes, with the graph
        argument as a subgraph, and with an edge (a, r) for each artist, a,
        from the artists argument and each related artist of a, r.
    """
    artists = {Artist(artist) for artist in artists}

    if graph is None:
        graph = nx.Graph()
    else:
        graph = graph.copy()

    graph.add_nodes_from(artists)

    for artist in artists:
        graph.add_edges_from((artist, related)
                             for related in artist.related())

    return graph


def grow(seeds, graph=None) -> nx.Graph:
    """
    Expands graph until the seed artists are connected by related artists.

    Args:
        seeds: An iterable of Artist objects or strings of artist IDs.
        graph: Optional; A networkx.Graph instance. graph is copied and not
            modified in-place. If graph is None, an empty graph is used.

    Returns:
        A networkx.Graph instance with Artist objects as nodes, with the graph
        argument as a subgraph, and with each object in the seeds argument
        within and connected to each other by paths of related artists.
    """
    seeds = {Artist(seed) for seed in seeds}

    if graph is None:
        graph = nx.Graph()
    else:
        graph = graph.copy()

    graph.add_nodes_from(seeds)

    new_artists = seeds

    while not all(nx.has_path(graph, source, target)
                  for source, target in combinations(seeds, 2)):
        new_graph = expand(new_artists, graph)
        new_artists = new_graph.nodes - graph.nodes
        graph = new_graph
        if not new_artists:
            raise RuntimeError("No new artists found.")

    for artist in new_artists:
        for related in artist.related():
            if related in graph.nodes:
                graph.add_edge(artist, related)  # new interconnections

    return graph


def trim(graph, keepers=()) -> nx.Graph:
    """
    Iteratively removes leaves from graph.

    Args:
        graph: A networkx.Graph instance. graph is copied and not modified
            in-place.
        keepers: Optional; A container of items to be kept in graph.

    Returns:
        A networkx.Graph instance. A subgraph of the graph argument without any
        leaves, except for nodes specified by the keepers argument (if any).
    """
    graph = graph.copy()

    # Remove leaves until none left.
    while True:
        to_remove = [x for x in graph.nodes
                     if graph.degree(x) < 2 and x not in keepers]
        if to_remove:
            graph.remove_nodes_from(to_remove)
        else:
            break

    return graph


def paths_subgraph(graph, seeds, max_len=None) -> (nx.Graph, dict):
    """
    Returns the subgraph of graph containing only the paths between seeds.

    Args:
        graph: A networkx.Graph instance. graph is copied and not modified
            in-place.
        seeds: An iterable containing nodes in the graph argument.
        max_len: Optional; If max_len is None, only the shortest paths between
            each pair of seeds will be included. Otherwise, only the paths with
            length <= max_len will be included.

    Returns:
        A tuple (G, paths_dict) containing a networkx.Graph instance (G) and
        a dictionary (paths_dict).

        G is a subgraph of the graph argument wherein each node belongs to one
        of the shortest simple paths between the nodes specified by the seeds
        argument.

        paths_dict maps pairs of seeds (as tuples) to the paths between them
        (as lists of lists).
    """
    graph = graph.copy()

    paths = {}

    for pair in combinations(seeds, 2):
        paths[pair] = []
        pair_max_len = max_len  # Specifically for when max_len is None.
        for path in nx.shortest_simple_paths(graph, *pair):
            if pair_max_len is None:
                paths[pair].append(path)
                # Set pair_max_len to shortest length between paired nodes.
                pair_max_len = len(paths[pair][-1])
            elif len(path) <= pair_max_len:
                paths[pair].append(path)
            else:  # nx.shortest_simple_paths yields paths of increasing length
                break

    keepers = set()

    for pair in paths:
        for path in paths[pair]:
            keepers.update(path)

    graph.remove_nodes_from(graph.nodes - keepers)

    return graph, paths


def plot(graph,
         seeds=(),  # for coloring purposes
         near_color="#6177aa",
         far_color="#0e1b3a",
         edge_color="#000102",
         font_color="#b9cdfb",
         fig_color="#2e4272",
         save=False,
         **plot_kwargs  # passed to nx.draw
         ) -> (plt.Figure, plt.Axes):
    """
    Plots the graph.

    The graph is plotted using networkx.draw_kamada_kawai. If the seeds
    argument is supplied, the nodes will vary in color based on proximity to
    the nodes in seeds, from near_color to far_color.

    Args:
        graph: A networkx.Graph instance.
        seeds: Optional; A container of items in graph. If supplied, the nodes,
            when plotted, will be colored based on proximity to the nodes in
            seeds.
        near_color: Optional; A string representing a color for matplotlib.
            The nodes in seeds will be this color. If the seeds argument is not
            supplied, all nodes will be this color.
        far_color: Optional; A string representing a color for matplotlib.
            The nodes farthest away from the nodes in seeds will be this color.
            If the seeds argument is not supplied, then no nodes will be this
            color.
        edge_color: Optional; A string representing a color for matplotlib.
        font_color: Optional; A string representing a color for matplotlib.
        fig_color: Optional; A string representing a color for matplotlib.
        save: If true, save the created plot to the /output directory.
            (For finer control, opt to instead use `fig.savefig(...)` from the
            returned plt.Figure object.)
        plot_kwargs: Optional; Keyword arguments to pass to networkx.draw (and
            to matplotlib, by extention).

    Returns:
        A tuple (fig, ax) containing the created plt.Figure (fig) and plt.Axes
        (ax) objects.
    """
    seeds = {Artist(seed) for seed in seeds}

    if seeds - graph.nodes:
        raise ValueError("Not all seeds are in graph.")

    dist = {seed: 0 for seed in seeds}

    if seeds and all(nx.has_path(graph, source, target)
                     for source, target in combinations(seeds, 2)):  # XXX
        pres = []
        dists = []

        for i, artist_id in enumerate(seeds):
            pres.append(nx.bfs_predecessors(graph, artist_id))
            dists.append({artist_id: 0})

        for i, artist_id in enumerate(seeds):
            for artist, pre in pres[i]:
                dists[i][artist] = dists[i][pre] + 1

        for artist_id in graph.nodes:
            dist[artist_id] = min(map(lambda d: d.get(artist_id, 1),
                                      dists))

    for artist_id in graph.nodes:
        if artist_id not in dist:
            dist[artist_id] = 1

    max_dist = max(max(dist.values()), 1)

    color = {k: dist[k] / max_dist for k in graph.nodes}

    node_labels = {artist_id:
                   Artist(artist_id).name.replace(r"$", r"\$")
                   for artist_id in graph.nodes}

    cmap = LinearSegmentedColormap.from_list("music",
                                             [near_color,
                                              far_color])

    fig, ax = plt.subplots(figsize=(16, 9))

    nx.draw_kamada_kawai(graph,
                         with_labels=True,
                         ax=ax,
                         cmap=cmap,
                         node_color=[color[k] for k in graph.nodes],
                         edge_color=edge_color,
                         font_color=font_color,
                         labels=node_labels,
                         **plot_kwargs
                         )

    fig.set_facecolor(fig_color)

    fig.tight_layout()

    if save:
        os.makedirs("output", exist_ok=True)
        fig.savefig("output/" +
                    "-".join(a.id for a in sorted(seeds)) +
                    ".png",
                    facecolor=fig_color)

    return fig, ax


def grow_and_plot(*seeds,
                  graph=None,
                  **plot_kw) -> (nx.Graph, (plt.Figure, plt.Axes)):
    """
    Grows and plots the graph grown from seeds.

    Grows the graph, trims it, gets the subgraph of its paths, and plots it.

    Args:
        seeds: Artist objects or strings of artist IDs
        graph: Optional; A networkx.Graph instance. graph is copied and not
            modified in-place. If graph is None, an empty graph is used.
        plot_kw: Optional; Keyword arguments to pass to networkx.draw (and
            to matplotlib, by extention).

    Returns:
        A tuple (G, (fig, ax)) containing a networkx.Graph instance (g) -- with
        Artist objects as nodes, and wherein each node belongs to one of the
        shortest simple paths of related artists between the nodes specified by
        the seeds argument -- and the created plt.Figure (fig) and plt.Axes
        (ax) objects.
    """
    seeds = {Artist(seed) for seed in seeds}

    graph = grow(seeds, graph=graph)
    graph = trim(graph, keepers=seeds)
    graph, _ = paths_subgraph(graph, seeds)

    return graph, plot(graph, seeds=seeds, **plot_kw)


if __name__ == "__main__":
    from artist_ids import ids

    grow_and_plot(ids["alice coltrane"], ids["erykah badu"])

    grow_and_plot(ids["alice coltrane"], ids["erykah badu"], ids["sun ra"])
