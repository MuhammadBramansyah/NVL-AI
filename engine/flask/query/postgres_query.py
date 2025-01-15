def get_data():
    return """
        select 
        id,stream_id,pixel_coordinates, 
        longitude, latitude ,
        location, stream_url
        from video_logs_2
        where status = 'A' 
        order by id desc
        limit 1
    """