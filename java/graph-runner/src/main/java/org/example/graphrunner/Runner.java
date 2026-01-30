package org.example.graphrunner;

import org.graphstream.graph.Edge;
import org.graphstream.graph.Graph;
import org.graphstream.graph.implementations.SingleGraph;
import org.graphstream.stream.file.FileSourceDGS;

public class Runner {
    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: Runner <graph.dgs>");
            System.exit(1);
        }
        String path = args[0];

        System.setProperty("org.graphstream.ui", "swing");

        Graph graph = new SingleGraph("players");
        graph.setAttribute("ui.stylesheet", Styles.CSS);
        graph.setAttribute("ui.quality");
        graph.setAttribute("ui.antialias");

        FileSourceDGS fs = new FileSourceDGS();
        fs.addSink(graph);
        fs.readAll(path);

        // Optional: size nodes by degree / edges by weight (already stored as attribute)
        for (Edge e : graph.getEachEdge()) {
            Object w = e.getAttribute("weight");
            if (w != null) e.setAttribute("ui.label", w.toString());
        }

        graph.display();
    }
}
