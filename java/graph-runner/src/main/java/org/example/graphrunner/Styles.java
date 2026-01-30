package org.example.graphrunner;

public class Styles {
    public static final String CSS = """
    graph { 
        padding: 60px; 
        fill-color: #f0eded;
    }
    
    node {
        text-size: 13;
        text-style: bold;
        text-alignment: under;
        fill-mode: dyn-plain;
        size: 12px;
        stroke-mode: plain;
        stroke-color: #000000;
        stroke-width: 2px;
    }
    
    edge {
        shape: line;
        size: 0.6px;
        fill-color: #7c7b7b;
        arrow-shape: none;
        text-size: 10;
    }
    """;
}