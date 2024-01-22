import argparse

import apache_beam as beam
import geopandas as gpd


def main(argv=None):
    """Main entry point; defines and runs the export pipeline."""

    gdf = gpd.read_file('/Users/kelmarkert/Downloads/NHDPlusCA 2/NHDPlus18/NHDSnapshot/NHDSnapshot.gdb', driver='FileGDB', layer='NHDFlowline')
    reach_ids = ','.join(map(str, gdf['Permanent_Identifier'].values[:20000]))

    print(len(reach_ids))

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--reference_time',
        type=str,
        required=True,
        help='The reference time of the forecast to export.'
    )

    parser.add_argument(
        '--runner',
        type=str,
        default='DirectRunner',
        choices=['DirectRunner', 'DataflowRunner'],
        help='The runner on which to execute the pipeline.'
    )

    args, pipeline_args = parser.parse_known_args()

    if pipeline_args is not None and args.runner == 'DataflowRunner':
        #define pipeline options
        opts = beam.pipeline.PipelineOptions(flags=pipeline_args)
    
    elif pipeline_args is None and args.runner == 'DataflowRunner':
        raise RuntimeError('No pipeline args were supplied with DataflowRunner.')
    
    elif pipeline_args is not None and args.runner == 'DirectRunner':
        opts = beam.pipeline.PipelineOptions(flags=pipeline_args)

    else:
        opts = None

    query = f'''
        SELECT 
            time, 
            reference_time, 
            streamflow, 
            velocity, 
            ensemble
        FROM
            `ciroh-water-demo.national_water_model_demo.channel_rt_long_range`
        WHERE 
            reference_time = "{args.reference_time}"
            AND feature_id IN ({", ".join(map(str, reach_ids.split(',')))})
    '''

    with beam.Pipeline(runner=args.runner, options=opts) as p:
        (p 
            | 'QueryTable' >> beam.io.ReadFromBigQuery(
                query=query,
                project='kmarkert-personal',
                gcs_location='gs://kmarkert_phd_research/nwm_dataflow_output/temp',
                use_standard_sql=True
            )
            | 'WriteToText' >> beam.io.WriteToText(
                'gs://kmarkert_phd_research/nwm_dataflow_output/long_range.csv'
            )
        )

    return


if __name__ == '__main__':
    main()