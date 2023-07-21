import requests
import json
import logging
import boto3
import time
from datetime import date
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)



bucket_name = "vwis-open-data-poc"

provider = TracerProvider()
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)

# Sets the global default tracer provider
trace.set_tracer_provider(provider)

# Creates a tracer from the global tracer provider
tracer = trace.get_tracer(__name__)


trace_id="None"
span_id="None"


FORMAT = '<Dextr>: [%(levelname)s]: %(asctime)s | Trace ID: %(trace_id)s Span ID: %(span_id)s | %(message)s'

extra={"trace_id": trace_id, "span_id": span_id}

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)





def lambda_handler(event, context):
    
    if "id" not in event:
        logging.LoggerAdapter(logger, extra).error("Id Not Provided")
        return {
            "statusCode":400,
            "body":"Id Not Provided"
        }
    
    if "url" not in event:
        logging.LoggerAdapter(logger, extra).error("url Not Provided")
        return {
            "statusCode":400,
            "body":"url Not Provided"
        }
    
   
    return handle_get_request(event, context)
 



def handle_get_request(event, context):
    start_time=time.time()
    with tracer.start_as_current_span("handle request") as parent_span:
        
        
        trace_id=parent_span.get_span_context().trace_id
        

        try:
            request=generate_request(event)

        except Exception as error:

            extra={"trace_id": trace_id, "span_id": parent_span.get_span_context().span_id}
            logging.LoggerAdapter(logger, extra).error("Request not generated")

            return {"statusCode": 400, "body": json.dumps(error)}
            
    
        with tracer.start_as_current_span("api request") as api_request_span:

            output=None

            try:
                output=api_request(request)
                output.raise_for_status()
                
            except requests.exceptions.RequestException as error:
    
                extra={"trace_id": trace_id, "span_id": api_request_span.get_span_context().span_id}
                if(output is None):
                    source=(event["url"].replace("https://","")).split("/")[0]
                    message=f"{source} not available"
                else:
                    message=f"Error Code {output.status_code}"

                logging.LoggerAdapter(logger, extra).error(f"API request failed: {message}" )
                return {
                    "statusCode": output.status_code if output is not None else 444,
                    "body":json.loads(json.dumps(error, default=str))
                }

        
        
        with open(f"/tmp/{event['id']}", "w") as file:
            file.write(output.text)
        

        with tracer.start_as_current_span("bucket writing") as bucket:
            write_bucket_output=write_bucket(event)


            if(write_bucket_output.__class__ is not bool):
            
                extra={"trace_id": trace_id, "span_id": bucket.get_span_context().span_id}
                logging.LoggerAdapter(logger, extra).error("Bucket not written")
                return {"statusCode": 401 if "AccessDenied" in write_bucket_output else 500,"body": json.loads(json.dumps(write_bucket_output, default=str))}
            

    extra={"trace_id": trace_id, "span_id": "None"}
    end_time = time.time()
    logging.LoggerAdapter(logger, extra).info(f"Done succesfully in {end_time - start_time}s" )

    return {"statusCode": 200, "body": "Done"}
    



def api_request(request):
    return requests.get(request)
        

def parameters_function(event):
    parameters = []
    if "sample_size_limit" in event["parameters"]:
        parameters.append(f"rows={event['parameters']['sample_size_limit']}")
    else:
        parameters.append(f"rows=10000")
    if "sort_criteria" in event["parameters"]:
        parameters.append(f"order_by={event['parameters']['sort_criteria']}")

    
    if("?" in event["url"].split("/")[-1]):
        return f"&{'&'.join(parameters)}"
    return f"?{'&'.join(parameters)}"


def generate_request(event):

    parameters="&rows=10000"
    url="Not assigned"
        
    if "parameters" in event:
        parameters=parameters_function(event)

    
    url=event["url"]
    
    return f"{url}{parameters}"
    





def write_bucket(event):

    source=(event["url"].replace("https://","")).split("/")[0]
    current_date=date.today().strftime("%Y/%m/%d")
    s3_client = boto3.client('s3')

    try:
        s3_client.upload_file(f"/tmp/{event['id']}", bucket_name, f"{source}/{current_date}/{event['id']}")
        return True
    except Exception as e:
        return e




