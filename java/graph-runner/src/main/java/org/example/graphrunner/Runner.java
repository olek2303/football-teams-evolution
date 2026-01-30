package org.example.graphrunner;

import org.graphstream.graph.Edge;
import org.graphstream.graph.Graph;
import org.graphstream.graph.implementations.SingleGraph;
import org.graphstream.stream.file.FileSourceDGS;
import org.graphstream.ui.view.Viewer;
import org.graphstream.graph.Node;

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

        // Assign unique colors to each node
        String[] colors = { 
            "#C0392B", "#117864", "#1a557c", "#D35400", "#196F3D", 
            "#6e5a08", "#884EA0", "#255474", "#A04000", "#5f270d", 
            "#CB4335", "#228049", "#A93226", "#5B2C6F", "#D81B60", 
            "#880E4F", "#a15818", "#145A32", "#154360", "#2e2605" 
        };
        
        int colorIndex = 0;

        for (Node node : graph.getEachNode()) {
            String color = colors[colorIndex % colors.length];

            node.setAttribute("ui.style", "fill-color: " + color + "; text-color: " + color + ";");
            
            colorIndex++;
        }

        // Optional: size nodes by degree / edges by weight (already stored as attribute)
        for (Edge e : graph.getEachEdge()) {
            Object w = e.getAttribute("weight");
            if (w != null) e.setAttribute("ui.label", w.toString());
        }
        
        Viewer viewer = graph.display();
        
        Thread.sleep(4000);
        viewer.disableAutoLayout();
    }
}
