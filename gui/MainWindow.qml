import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtGraphs

Window {
    visible: true
    width: 1280
    height: 720
    title: "Twist & Tune GUI"
    
    Rectangle {
        id: mainContainer
        anchors.fill: parent
        color: "#ffffff"

        Text {
            id: title
            text: qsTr("Twist & Tune GUI")
            font.family: "Tahoma"
            font.styleName: "Bold"
            font.pointSize: 36
            anchors.verticalCenterOffset: -308
            anchors.horizontalCenterOffset: 0
            anchors.centerIn: parent
        }

        Slider {
            id: setpointSlider
            objectName: "setpointSlider"
            x: 144
            y: 633
            value: 0.5
        }

        Text {
            id: setpointText
            objectName: "setpointText"
            x: 148
            y: 600
            text: qsTr("Target Speed: 300rpm")
            font.pixelSize: 20
        }

        Text {
            id: kpText
            objectName: "kpText"
            x: 428
            y: 651
            text: qsTr("KP Gain: 0.0")
            font.pixelSize: 22
        }

        Text {
            id: kiText
            objectName: "kiText"
            x: 638
            y: 651
            text: qsTr("KI Gain: 0.0")
            font.pixelSize: 22
        }

        Text {
            id: kdText
            objectName: "kdText"
            x: 853
            y: 651
            text: qsTr("KD Gain: 0.0")
            font.pixelSize: 22
        }

        Text {
            id: speedText
            objectName: "speedText"
            x: 585
            y: 608
            text: qsTr("Actual Speed: 300rpm")
            font.pixelSize: 22
        }

        GraphsView {
            id: graph
            objectName: "graph"
            x: 93
            y: 103
            width: 1092
            height: 465
            opacity: 1

            theme: GraphsTheme {
                colorScheme: Qt.Light
                grid.mainColor: "#e0e0e0" // Light gray for the grid lines
                labelTextColor: "black"
            }

            ValueAxis {
                id: valueAxisX
                objectName: "graphAxisX"
                min: 0
                max: 10
            }

            ValueAxis {
                id: valueAxisY
                min: 0
                max: 600
            }

            SplineSeries {
                id: lineSeries
                objectName: "speedGraphData"
                color: "red"
                axisX: valueAxisX
                axisY: valueAxisY
            }

            LineSeries {
                id: lineSeries
                objectName: "setpointGraphData"
                color: "blue"
                axisX: valueAxisX
                axisY: valueAxisY
            }
        }
    }
}
