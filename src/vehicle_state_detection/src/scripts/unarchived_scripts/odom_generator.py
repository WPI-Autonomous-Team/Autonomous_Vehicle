#!/usr/bin/env python
import rospy, math
from utm import from_latlon
from tf.transformations import quaternion_from_euler
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TwistStamped
from custom_msgs.msg import positionEstimate, orientationEstimate
from dbw_mkz_msgs.msg import WheelSpeedReport


class OdomGenerator():

	def __init__(self):

		rospy.init_node('odom_generator', anonymous=True)

		self.sub_datum = rospy.Subscriber("/mti/filter/position", positionEstimate, self.datumUpdate)
		rospy.Subscriber("/mti/filter/orientation", orientationEstimate, self.odomOrientationUpdate)
		rospy.Subscriber("/vehicle/wheel_speed_report", WheelSpeedReport, self.odomPositionUpdate)
		rospy.Subscriber("/vehicle/twist", TwistStamped, self.odomTwistUpdate)

		# publishers for vehicle localization...
		self.pub_odom = rospy.Publisher("/vehicle/odom/data_raw", Odometry, queue_size=10)

		self.odom_data = self.initializeOdom()

		self.latitude_datum = 42.275921
		self.longitude_datum = -71.798370
		self.easting_datum = from_latlon(self.latitude_datum, self.longitude_datum)[0]
		self.northing_datum = from_latlon(self.latitude_datum, self.longitude_datum)[1]		

		self.odom_x = 0
		self.odom_y = 0
		self.odomYaw = 0

		self.canBusTimeInterval = 0.01
		self.wheelRadius = 0.34036 #FIXME Need measurements!
		self.trackWidth = 1.57861

		self.datumReceived  = False
		self.orientationReceived = False
		self.twistReceived = False
		self.wheelSigReceived = False

		self.publishOdom()

	def publishOdom(self):
		while not rospy.is_shutdown():
			rospy.loginfo("waiting for Subscribers...")
			rospy.sleep(0.5)
			while not rospy.is_shutdown() and self.datumReceived and self.orientationReceived and self.twistReceived and self.wheelSigReceived:
				self.publishOdomMsg()
				rospy.sleep(0.02)

	# subscriber callback functions:
	def datumUpdate(self, data):
		if not self.datumReceived:
			# determine the first starting point. Run only once.
			easting = from_latlon(data.latitude, data.longitude)[0]
			northing = from_latlon(data.latitude, data.longitude)[1]
			self.odom_x = easting-self.easting_datum
			self.odom_y = northing-self.northing_datum
			self.datumReceived = True
			self.sub_datum.unregister()

	def odomPositionUpdate(self, data):
		self.wheelSigReceived = True
		speed = self.wheelRadius*(data.front_left + data.front_right + data.rear_left + data.rear_right)/4
		self.odom_x = self.odom_x + speed*self.canBusTimeInterval*math.cos(self.odomYaw)
		self.odom_y = self.odom_y + speed*self.canBusTimeInterval*math.sin(self.odomYaw)
		self.odom_data.header.stamp = rospy.Time.now()
		self.odom_data.pose.pose.position.x = self.odom_x
		self.odom_data.pose.pose.position.y = self.odom_y
		self.odom_data.pose.pose.position.z = 0

	def odomOrientationUpdate(self, data):
		self.orientationReceived = True
		self.odom_data.header.stamp = rospy.Time.now()
		self.odomYaw = math.radians(data.yaw)
		quaternion = quaternion_from_euler(0, 0, self.odomYaw)
		self.odom_data.pose.pose.orientation.x = quaternion[0]
		self.odom_data.pose.pose.orientation.y = quaternion[1]
		self.odom_data.pose.pose.orientation.z = quaternion[2]
		self.odom_data.pose.pose.orientation.w = quaternion[3]

	def odomTwistUpdate(self, data):
		self.twistReceived = True
		self.odom_data.header.stamp = rospy.Time.now()
		self.odom_data.twist.twist = data.twist

	# publishing functions
	def publishOdomMsg(self):
		self.pub_odom.publish(self.odom_data)

	# initialize the publishing messages:
	def initializeOdom(self):
		msg = Odometry()
		msg.header.stamp = rospy.Time.now()
		msg.header.frame_id = "odom"
		msg.child_frame_id = "base_link"
		msg.pose.pose.orientation.w = 1
		msg.pose.covariance = [0, 0, 0, 0, 0, 0,
							   0, 0, 0, 0, 0, 0,
							   0, 0, 0, 0, 0, 0,
							   0, 0, 0, 0, 0, 0,
							   0, 0, 0, 0, 0, 0,
							   0, 0, 0, 0, 0, 0]
		msg.twist.covariance = [0, 0, 0, 0, 0, 0,
							    0, 0, 0, 0, 0, 0,
							    0, 0, 0, 0, 0, 0,
							    0, 0, 0, 0, 0, 0,
							    0, 0, 0, 0, 0, 0,
							    0, 0, 0, 0, 0, 0]
		return msg

def main():
	OdomGenerator()
	rospy.spin()


if __name__== '__main__':
	try:
		main()
	except rospy.ROSInterruptException:
		pass
