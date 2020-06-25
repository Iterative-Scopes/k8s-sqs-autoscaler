import boto3
import os
from time import sleep, time
from logs.log import logger
from kubernetes import client, config
import yaml

class SQSPoller:

    options = None
    sqs_client = None
    apps_v1 = None
    last_message_count = None

    def __init__(self, options):
        self.options = options
        self.sqs_client = boto3.client('sqs')
        config.load_incluster_config()
        self.apps_v1 = client.AppsV1Api()
        self.last_scale_up_time = time()
        self.last_scale_down_time = time()

    def message_count(self):
        response = self.sqs_client.get_queue_attributes(
            QueueUrl=self.options.sqs_queue_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        return int(response['Attributes']['ApproximateNumberOfMessages'])


    def poll(self):
        message_count = self.message_count()
        t = time()
        if  message_count >= self.options.scale_up_messages:
            if t - self.last_scale_up_time > self.options.scale_up_cool_down:
                #if deployment is zero - deploy a new service using yaml file.
                if self.deployment() == 0:
                    logger.info("no deployments found")
                    self.create_deployment()
                else:
                    self.scale_up()
                self.last_scale_up_time = t
            else:
                logger.info("Waiting for scale up cooldown")
        if message_count <= self.options.scale_down_messages:
            if t - self.last_scale_down_time > self.options.scale_down_cool_down:
                self.scale_down()
                self.last_scale_down_time = t
            else:
                logger.info("Waiting for scale down cooldown")

        # code for scale to use msg_count
        sleep(self.options.poll_period)

    def create_deployment(self):
        logger.info("creating a new deployment")
        #TODO create a deployment
        with open(os.path.join(os.path.dirname(__file__), self.options.kubernetes_deployment_file)) as f:
            logger.info("using deployment file {}")
            dep = yaml.safe_load(f)
            k8s_apps_v1 = client.AppsV1Api()
            resp = k8s_apps_v1.create_namespaced_deployment(
                body=dep, 
                namespace=self.options.kubernetes_namespace
            )
            logger.info("Deployment created. status='%s'" % resp.metadata.name)

    def scale_up(self):
        deployment = self.deployment()
        if deployment.spec.replicas < self.options.max_pods:
            logger.info("Scaling up")
            deployment.spec.replicas += 1
            self.update_deployment(deployment)
        elif deployment.spec.replicas > self.options.max_pods:
            self.scale_down()
        else:
            logger.info("Max pods reached")

    def scale_down(self):
        deployment = self.deployment()
        if deployment.spec.replicas > self.options.min_pods:
            logger.info("Scaling Down")
            deployment.spec.replicas -= 1
            self.update_deployment(deployment)
        elif deployment.spec.replicas < self.options.min_pods:
            self.scale_up()
        else:
            logger.info("Min pods reached")

    def deployment(self):
        logger.info("loading deployment: {} from namespace: {}".format(self.options.kubernetes_deployment, self.options.kubernetes_namespace))
        deployments = self.apps_v1.list_namespaced_deployment(self.options.kubernetes_namespace, label_selector="app={}".format(self.options.kubernetes_deployment))
        try:
            return deployments.items[0]
        except:
            return 0

    def update_deployment(self, deployment):
        # Update the deployment
        api_response = self.apps_v1.patch_namespaced_deployment(
            name=self.options.kubernetes_deployment,
            namespace=self.options.kubernetes_namespace,
            body=deployment)
        logger.info("Deployment updated. status='%s'" % str(api_response.status))

    def run(self):
        options = self.options
        logger.info("Starting poll for {} every {}s".format(options.sqs_queue_url, options.poll_period))
        while True:
            self.poll()

def run(options):
    """
    poll_period is set as as part of k8s deployment env variable
    sqs_queue_url is set as as part of k8s deployment env variable
    """
    SQSPoller(options).run()

