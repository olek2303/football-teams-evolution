package com.football;

import org.graphstream.graph.*;
import org.graphstream.graph.implementations.*;
import org.graphstream.ui.view.Viewer;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

public class FootballGraph {


    private static final String CSV_FILE = "./files/fc-barcelona_edges.csv";

//    show only edges with value greater than...
    private static final int MIN_MATCHES_WEIGHT = 200;

    public static void main(String[] args) {

        System.setProperty("org.graphstream.ui", "swing");


        Graph graph = new SingleGraph("FC Barcelona Evolution");


        loadGraphFromCSV(graph, CSV_FILE);


        applyStyles(graph);


        Viewer viewer = graph.display();
        viewer.enableAutoLayout();
    }

    private static void loadGraphFromCSV(Graph graph, String filePath) {
        String line;
        String cvsSplitBy = ",";

        System.out.println("Loading graph...");

        try (BufferedReader br = new BufferedReader(new FileReader(filePath))) {

            br.readLine();

            while ((line = br.readLine()) != null) {
                String[] data = line.split(cvsSplitBy);


                if(data.length < 3) continue;

                String player1 = data[0].trim();
                String player2 = data[1].trim();
                double weight = Double.parseDouble(data[2]);


                if (weight < MIN_MATCHES_WEIGHT) {
                    continue;
                }


                if (graph.getNode(player1) == null) {
                    Node n = graph.addNode(player1);
                    n.setAttribute("ui.label", player1);
                }
                if (graph.getNode(player2) == null) {
                    Node n = graph.addNode(player2);
                    n.setAttribute("ui.label", player2);
                }


                String edgeId = player1 + "-" + player2;


                if (graph.getEdge(edgeId) == null) {
                    Edge edge = graph.addEdge(edgeId, player1, player2);
                    edge.setAttribute("weight", weight);


                    double thickness = weight / 50.0;
                    if(thickness < 1) thickness = 1; // Minimum 1px

                    edge.setAttribute("ui.style", "size: " + thickness + "px;");
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }

        System.out.println("Węzłów: " + graph.getNodeCount() + ", Krawędzi: " + graph.getEdgeCount());
    }

    private static void applyStyles(Graph graph) {

        String styleSheet =
                "graph { " +
                        "fill-color: #f0f0f0; " +
                        "} " +
                        "node { " +
                        "fill-color: #A00; " +
                        "size: 15px; " +
                        "text-color: #222; " +
                        "text-size: 12; " +
                        "stroke-mode: plain; " +
                        "stroke-color: #111; " +
                        "} " +
                        "edge { " +
                        "fill-color: #113; " +
                        "text-mode: hidden; " +
                        "} " +

                        "node:clicked { " +
                        "fill-color: red; " +
                        "}";

        graph.setAttribute("ui.stylesheet", styleSheet);
        graph.setAttribute("ui.quality");
        graph.setAttribute("ui.antialias");
    }
}