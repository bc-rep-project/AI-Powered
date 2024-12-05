from typing import List, Dict, Any, Optional
import pandas as pd
import json
from io import BytesIO
import xlsxwriter
from datetime import datetime
from .database import Database

class DataExport:
    @classmethod
    async def export_data(
        cls,
        data_type: str,
        format: str,
        filters: Dict[str, Any] = None,
        custom_query: Dict = None
    ) -> tuple[bytes, str]:
        """Export data in various formats"""
        # Get data based on type
        if data_type == "interactions":
            data = await cls._get_interaction_data(filters, custom_query)
            filename = f"interactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        elif data_type == "recommendations":
            data = await cls._get_recommendation_data(filters, custom_query)
            filename = f"recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        elif data_type == "user_segments":
            data = await cls._get_user_segment_data(filters, custom_query)
            filename = f"user_segments_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        # Convert to specified format
        if format == "csv":
            output = cls._to_csv(data)
            content_type = "text/csv"
            filename = f"{filename}.csv"
        elif format == "excel":
            output = cls._to_excel(data)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{filename}.xlsx"
        elif format == "json":
            output = cls._to_json(data)
            content_type = "application/json"
            filename = f"{filename}.json"
        else:
            raise ValueError(f"Unsupported format: {format}")

        return output, content_type, filename

    @staticmethod
    async def _get_interaction_data(
        filters: Optional[Dict] = None,
        custom_query: Optional[Dict] = None
    ) -> List[Dict]:
        """Get interaction data with filters"""
        query = custom_query if custom_query else {}
        
        if filters:
            if filters.get("start_date"):
                query["timestamp"] = query.get("timestamp", {})
                query["timestamp"]["$gte"] = filters["start_date"]
            if filters.get("end_date"):
                query["timestamp"] = query.get("timestamp", {})
                query["timestamp"]["$lte"] = filters["end_date"]
            if filters.get("user_id"):
                query["user_id"] = filters["user_id"]
            if filters.get("content_id"):
                query["content_id"] = filters["content_id"]
            if filters.get("interaction_type"):
                query["interaction_type"] = filters["interaction_type"]

        interactions = await Database.db.interactions.find(query).to_list(None)
        return interactions

    @staticmethod
    async def _get_recommendation_data(
        filters: Optional[Dict] = None,
        custom_query: Optional[Dict] = None
    ) -> List[Dict]:
        """Get recommendation data with filters"""
        query = custom_query if custom_query else {}
        
        if filters:
            if filters.get("start_date"):
                query["timestamp"] = query.get("timestamp", {})
                query["timestamp"]["$gte"] = filters["start_date"]
            if filters.get("end_date"):
                query["timestamp"] = query.get("timestamp", {})
                query["timestamp"]["$lte"] = filters["end_date"]
            if filters.get("algorithm_version"):
                query["algorithm_version"] = filters["algorithm_version"]
            if filters.get("user_id"):
                query["user_id"] = filters["user_id"]

        recommendations = await Database.db.recommendation_history.find(query).to_list(None)
        return recommendations

    @staticmethod
    async def _get_user_segment_data(
        filters: Optional[Dict] = None,
        custom_query: Optional[Dict] = None
    ) -> List[Dict]:
        """Get user segment data"""
        from .visualization import Visualization
        
        days = filters.get("days", 30) if filters else 30
        n_segments = filters.get("n_segments", 4) if filters else 4
        
        segments_data = await Visualization.generate_user_segments(days, n_segments)
        return segments_data.get("user_segments", [])

    @staticmethod
    def _to_csv(data: List[Dict]) -> bytes:
        """Convert data to CSV format"""
        df = pd.DataFrame(data)
        output = BytesIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    @staticmethod
    def _to_excel(data: List[Dict]) -> bytes:
        """Convert data to Excel format"""
        df = pd.DataFrame(data)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Data', index=False)
            
            # Auto-adjust columns width
            worksheet = writer.sheets['Data']
            for i, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                ) + 2
                worksheet.set_column(i, i, max_length)

        return output.getvalue()

    @staticmethod
    def _to_json(data: List[Dict]) -> bytes:
        """Convert data to JSON format"""
        return json.dumps(data, default=str).encode('utf-8')

    @classmethod
    async def export_dashboard(
        cls,
        dashboard_type: str,
        format: str = "pdf",
        filters: Dict[str, Any] = None
    ) -> bytes:
        """Export entire dashboard as PDF or image"""
        from .visualization import Visualization
        
        if dashboard_type == "user_segments":
            dashboard_data = await Visualization.generate_user_segments()
        elif dashboard_type == "recommendations":
            dashboard_data = await Visualization.generate_recommendation_insights()
        elif dashboard_type == "content":
            if not filters or "content_id" not in filters:
                raise ValueError("content_id is required for content dashboard export")
            dashboard_data = await Visualization.generate_content_drill_down(
                filters["content_id"]
            )
        else:
            raise ValueError(f"Unsupported dashboard type: {dashboard_type}")

        # Combine all visualizations into a single PDF/image
        import plotly.subplots as sp
        
        # Create a subplot figure
        fig = sp.make_subplots(
            rows=len(dashboard_data),
            cols=1,
            subplot_titles=list(dashboard_data.keys())
        )
        
        # Add each visualization to the subplot
        row = 1
        for key, chart_json in dashboard_data.items():
            if isinstance(chart_json, str) and chart_json.startswith("{"):
                chart_data = json.loads(chart_json)
                fig.add_trace(chart_data["data"][0], row=row, col=1)
                row += 1

        # Update layout
        fig.update_layout(
            height=400 * row,  # Adjust height based on number of visualizations
            title_text=f"{dashboard_type.title()} Dashboard Export"
        )

        # Export as specified format
        if format == "pdf":
            return fig.to_image(format="pdf")
        else:
            return fig.to_image(format=format) 