"""
plots.py
========
Konkrete Plot-Klassen für das Dashboard.
"""
import plotly.express as px
import plotly.graph_objects as go
from src.visualizations.base_plot import BasePlot


class InvestmentHeatmapPlot(BasePlot):
    """Predictive Map: Investment-Heatmap (Gap Index) auf Gemeindeebene."""

    def __init__(self, gdf, color_col="Predicted_Gap_Index", hover_name="PLZ", color_safe_mode=False, range_color=None):
        """
        gdf: GeoDataFrame mit den Daten.
        color_col: Spalte, die für die Einfärbung (Heatmap) genutzt wird.
        """
        self.gdf = gdf
        self.color_col = color_col
        self.hover_name = hover_name
        self.color_safe_mode = color_safe_mode
        self.range_color = range_color

    def render(self):
        # Wir stellen sicher, dass wir in WGS84 (EPSG:4326) sind für Mapbox
        if not self.gdf.empty and self.gdf.crs is not None and self.gdf.crs.to_string() != "EPSG:4326":
            plot_gdf = self.gdf.to_crs("EPSG:4326")
        else:
            plot_gdf = self.gdf

        # Perfekte Zentrierung für die gesamte Schweiz oder Einzelregionen
        if not plot_gdf.empty:
            if len(plot_gdf) > 10:  # Gesamte Schweiz (Kantone=26, Gemeinden>2000)
                center_lat = 46.8182
                center_lon = 8.2275
                zoom_level = 6.2
            else:  # Einzelne Region / Suchergebnis
                try:
                    center_lat = plot_gdf.geometry.centroid.y.mean()
                    center_lon = plot_gdf.geometry.centroid.x.mean()
                    zoom_level = 8.0
                except Exception:
                    center_lat, center_lon = 46.8182, 8.2275
                    zoom_level = 7.3
        else:
            center_lat, center_lon = 46.8182, 8.2275
            zoom_level = 7.3

        # Farbskala und Bereich dynamisch bestimmen
        min_val = plot_gdf[self.color_col].min()
        max_val = plot_gdf[self.color_col].max()
        
        if self.range_color is not None:
            range_color = self.range_color
            if self.color_safe_mode:
                color_scale = "Cividis"
            elif min_val < 0 or range_color[0] < 0:
                color_scale = [
                    [0.0, "#0000FF"], # Tiefblau (-100)
                    [0.5, "#90EE90"], # Hellgrün (0)
                    [1.0, "#FF0000"]  # Rot (100+)
                ]
            else:
                color_scale = "RdYlGn_r"
        elif self.color_safe_mode:
            # Barrierefreie Skala: Cividis ist optimal für alle Arten der Farbenblindheit
            color_scale = "Cividis"
            range_color = [min_val, max_val] if min_val < max_val else [0, 1]
        elif min_val < 0:
            # Divergierende Skala: Blau (Überfluss) -> Hellgrün (Neutral) -> Rot (Bedarf)
            color_scale = [
                [0.0, "#0000FF"], # Tiefblau (-100)
                [0.5, "#90EE90"], # Hellgrün (0)
                [1.0, "#FF0000"]  # Rot (100+)
            ]
            limit = max(abs(min_val), abs(max_val))
            range_color = [-limit, limit]
        else:
            color_scale = "RdYlGn_r"
            range_color = [0, max_val] if max_val > 0 else [0, 1]

        # Spalten für Tooltip auswählen
        custom_data_cols = [c for c in ["Elektro_Prognose", "Anzahl_Ladestationen", "Predicted_Gap", "Predicted_Gap_Index"] if c in plot_gdf.columns]
        
        fig = px.choropleth_mapbox(
            plot_gdf,
            geojson=plot_gdf.geometry,
            locations=plot_gdf.index,
            color=self.color_col,
            color_continuous_scale=color_scale,
            range_color=range_color,
            mapbox_style="carto-positron",
            zoom=zoom_level,
            center={"lat": center_lat, "lon": center_lon},
            opacity=0.7,
            hover_name=self.hover_name,
            custom_data=custom_data_cols,
            labels={
                "Predicted_Gap_Index": "Bedarf Index",
                "Predicted_Gap": "Bedarf",
                "Elektro_Prognose": "E-Fahrzeuge",
                "Anzahl_Ladestationen": "Ladestationen"
            }
        )
        
        template = "<b>%{hovertext}</b><br>"
        for i, col in enumerate(custom_data_cols):
            if col == "Elektro_Prognose": template += "E-Fahrzeuge: %{customdata[" + str(i) + "]:.0f}<br>"
            elif col == "Anzahl_Ladestationen": template += "Ladestationen: %{customdata[" + str(i) + "]:.0f}<br>"
            elif col == "Predicted_Gap": template += "Bedarf: %{customdata[" + str(i) + "]:.0f}<br>"
            elif col == "Predicted_Gap_Index": template += "Bedarf Index: %{customdata[" + str(i) + "]:.1f}<br>"
        
        template += "<extra></extra>"
        fig.update_traces(hovertemplate=template)
        
        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_colorbar=dict(
                title=dict(text="Bedarf", font=dict(size=14)),
                thicknessmode="pixels", thickness=15,
                lenmode="fraction", len=0.8,
                yanchor="bottom", y=0.02,
                ticks="outside",
                tickvals=[range_color[0], 0, range_color[1]] if not self.color_safe_mode and min_val < 0 else None
            )
        )
        return fig


class GrowthOverTimePlot(BasePlot):
    """Deskriptiver Plot: Historische Neuzulassungen oder Bestand über die Zeit."""

    def __init__(self, df_time, x_col="Jahr", y_cols=["Elektro", "Hybrid", "Verbrenner"], color_safe_mode=False):
        self.df_time = df_time
        self.x_col = x_col
        self.y_cols = [col for col in y_cols if col in df_time.columns]
        self.color_safe_mode = color_safe_mode

    def render(self):
        # Farbschema (Okabe-Ito für Barrierefreiheit)
        if self.color_safe_mode:
            colors = ["#0072B2", "#E69F00", "#56B4E9"] # Blau, Orange, Hellblau
        else:
            colors = ["#00CC96", "#AB63FA", "#EF553B"] # Standard (Grün, Violett, Rot)

        fig = px.area(
            self.df_time, 
            x=self.x_col, 
            y=self.y_cols,
            title="Entwicklung der Antriebsarten über Zeit",
            color_discrete_sequence=colors,
            labels={"value": "Anzahl Fahrzeuge", "variable": "Antriebsart"}
        )
        
        fig.update_traces(opacity=1.0)
        
        if "Gesamt" in self.df_time.columns:
            fig.add_scatter(
                x=self.df_time[self.x_col],
                y=self.df_time["Gesamt"],
                name="Gesamtbestand",
                line=dict(color="white", width=3, dash="dot"),
                hovertemplate="Gesamt: %{y:,.0f}"
            )
        
        fig.update_layout(
            hovermode="x unified",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family":"Inter, sans-serif"},
            legend={"orientation":"h", "yanchor":"bottom", "y":1.02, "xanchor":"right", "x":1}
        )
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_xaxes(showgrid=False)
        return fig


class EngineDistributionPlot(BasePlot):
    """Deskriptiver Plot: Verteilung der aktuellen Antriebsarten."""

    def __init__(self, df, value_cols=["Elektro", "Hybrid", "Verbrenner"], color_safe_mode=False):
        self.df = df
        self.value_cols = [col for col in value_cols if col in df.columns]
        self.color_safe_mode = color_safe_mode

    def render(self):
        sums = []
        for col in self.value_cols:
            sums.append(self.df[col].sum())

        clean_labels = [label.replace("_Prognose", "").replace("_", " ") for label in self.value_cols]
        
        if self.color_safe_mode:
            colors = ["#0072B2", "#E69F00", "#56B4E9"]
        else:
            colors = ["#00CC96", "#AB63FA", "#EF553B"]
            
        fig = go.Figure(data=[go.Pie(
            labels=clean_labels, 
            values=sums,
            hole=.4,
            marker_colors=colors,
            textinfo='label+percent',
            textposition='outside',
            insidetextorientation='horizontal',
            hoverinfo='label+value+percent'
        )])
        
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family":"Inter, sans-serif"},
            showlegend=False
        )
        return fig

