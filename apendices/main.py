#!/bin/env python3
import numpy as np
from numpy.random import randn
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['text.usetex'] = True
import time
from pdb import set_trace


# Parameters
DATA_L=1000
MASS=1 # Kg
G_CONSTANT=9.8 # m/s^2
INERTIA=MASS*0.45**2/12 # Kg.m^2 
DT=0.01 # s # Reducir el paso mejora la precisión de la predicción, aunque haya ruido 

#ACCEL_NOISE = 0.35 # m/s^2
ACCEL_NOISE = 1 # m/s^2
#GYRO_NOISE = 0.015 # rad/s
GYRO_NOISE = 0.03 # rad/s
#GPS_NOISE= 0.7 # m 
GPS_NOISE= 0.1 # m 
VISION_NOISE = 0.05 # m 

# Plot flags
DRAW_ESTIMATED = True
IMAGE_FOLDER = 'images/'
IMAGE_EXTENSION = 'png'


# Control se realiza sobre los estados reales para acotar más el efecto del estimador
def control_actuators(theta: float, thetad: float ,theta_ref:float, yd_e: float) -> [float,float]:
    # Control gains
    K_height = 2
    K_tilt = 0.2
    Kd_tilt = 0.1
    thrust = MASS*G_CONSTANT/np.cos(theta) + yd_e*K_height
    torque = (theta_ref-theta)*K_tilt -thetad*Kd_tilt
    return thrust, torque

def draw_animation(x,y,theta):
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    
    fig, ax = plt.subplots()
    xdata, ydata = [], []
    ln, = plt.plot([], [], 'r')
    ln2, = plt.plot([], [], 'b')
    
    
    def init():
        margin=2
        ax.set_xlim(min(x)-margin, max(x)+margin)
        ax.set_ylim(min(y)-margin, max(y)+margin)
        ax.set_aspect('equal')
        return ln,
    
    def update(frame):
        xdata.append(x[frame])
        ydata.append(y[frame])
        ln.set_data(xdata, ydata)
        c = np.cos(theta[frame])
        s = np.sin(theta[frame])
        rot_mat = np.array([[c, -s], [s, c]])
        p1 = [-0.5,0]
        p2 = [0.5,0]
        p1_rot = rot_mat @ p1
        p2_rot = rot_mat @ p2
        ln2.set_data([p1_rot[0],p2_rot[0]]+x[frame], [p1_rot[1],p2_rot[1]]+y[frame])
        return ln,ln2
    
    ani = FuncAnimation(fig, update, frames=len(x), 
                        init_func=init, blit=True, interval=DT*1e3,repeat=False)
    plt.show()

def main():
    print("-------------------")
    print("Simulador quadrotor")
    print("-------------------")

    # Actuation signals
    thrust = np.ones( DATA_L )*MASS*G_CONSTANT
    torque = np.zeros( DATA_L )

    # translational varibles
    a = np.zeros( (2,DATA_L) )
    v = np.zeros( (2,DATA_L) )
    p = np.zeros( (2,DATA_L) )

    # angular variables. Initialized in zero
    theta = np.zeros( DATA_L )
    thetad = np.zeros( DATA_L )
    thetadd = np.zeros( DATA_L )

    # sensores
    accel = np.zeros( (2,DATA_L) )
    accel_gt = np.zeros( (2,DATA_L) )
    gyro = np.zeros( DATA_L )
    gps = np.zeros( (2,DATA_L) )
    vision = np.zeros( (2,DATA_L) )
    # add optical flow
    op_flow = np.zeros( DATA_L )

    # Setpoints
    yd_ref = np.zeros( DATA_L )
    theta_ref = np.zeros( DATA_L )
    yd_ref[                     :int(DATA_L*0.25)    ] = 2
    theta_ref[int(DATA_L*0.70)  :int(DATA_L*0.85)    ] = np.pi/6 
    theta_ref[int(DATA_L*0.85)  :                    ] = -np.pi/6 

    t = np.array(list(range(DATA_L)))*DT
    

    # Simulate 2 newton law
    # Simular despegue y avance dibujando el suelo
    for i in range(1,DATA_L): # Pass states are needed, so we start at second
        # Control actuators
        thrust[i], torque[i] =  control_actuators(theta[i-1],thetad[i-1], theta_ref[i], yd_ref[i] - v[1,i-1])

        # Rotational dynamics
        thetadd[i] = torque[i]/INERTIA
        thetad[i] = thetad[i-1] + DT*thetadd[i] # TODO: test trapezoidal integration
        theta[i] = theta[i-1] + DT*thetad[i] 

        # Rotation matrix. Transform body coodinates to inertial coordinates
        c = np.cos(theta[i])
        s = np.sin(theta[i])
        rot_mat = np.array([[c, -s], [s, c]])

        # Translational dynamics
        thrust_rot= rot_mat @ np.array([0, thrust[i]])
        gravity_force = np.array([0, -G_CONSTANT])*MASS 
        a[:,i] = (thrust_rot+gravity_force)/MASS
        v[:,i] = v[:,i-1] + DT*a[:,i] 
        p[:,i] = p[:,i-1] + DT*v[:,i] 

        # simulate sensors
        accel_gt[:,i] = np.linalg.inv(rot_mat) @ a[:,i]
        accel[:,i] = accel_gt[:,i] + randn(2)*ACCEL_NOISE # TODO: Habría que multiplicarlo por la inversa de rot_mat?
        gps[:,i] = p[:,i] + randn(2)*GPS_NOISE
        vision[:,i] = p[:,i] + randn(2)*VISION_NOISE
        gyro[i] = thetad[i] + randn(1)*GYRO_NOISE

        
    # States estimation
    v_est = np.zeros( (2,DATA_L) )
    p_est = np.zeros( (2,DATA_L) )
    theta_est = np.zeros( DATA_L )

    # Matriz de covarianzas
    P_est = np.zeros( (5,5,DATA_L) )

    # Error en la predicción # TODO: calcularlo a partir de los ruidos de los sensores
    Q = np.zeros( (5,5) )

    # Jacobianos de los modelos de observación 
    H_vision = np.zeros((2,5))
    H_vision[0,0]=1
    H_vision[1,1]=1
    R_vision = np.diag([VISION_NOISE**2, VISION_NOISE**2])

    H_gps = np.zeros((2,5))
    H_gps[0,0]=1
    H_gps[1,1]=1
    R_gps = np.diag([GPS_NOISE**2, GPS_NOISE**2])

    # Initalization 
    for i in range(1,DATA_L):
        # Prediction de los estados
        theta_pred = theta_est[i-1] + DT*gyro[i] 
        c = np.cos(theta_pred) 
        s = np.sin(theta_pred)
        # TODO: utilizar aquí el predicho ahora o el estimado anterior?
        #c = np.cos(theta_est[i-1]) 
        #s = np.sin(theta_est[i-1])
        rot_mat = np.array([[c, -s], [s, c]])
        v_pred = v_est[:,i-1] + DT*rot_mat @ accel[:,i] 
        p_pred = p_est[:,i-1] + DT*v_est[:,i-1] 

        # Predicción de la matriz de covarianzas
        x_pred=np.array([p_pred[0], p_pred[1], v_pred[0], v_pred[1], theta_pred])
        F = np.array([
                       [1,0,DT,0 ,0],
                       [0,1,0 ,DT,0],
                       [0,0,1 ,0,DT*(-accel[0,i]*np.sin(theta_pred) + accel[1,i]*np.cos(theta_pred) )], 
                       [0,0,0 ,1,DT*(-accel[0,i]*np.cos(theta_pred) - accel[1,i]*np.sin(theta_pred) )],
                       [0,0,0 ,0 ,1],
            ])
        G = np.array([
                [0      ,0      ,0],
                [0      ,0      ,0], # que pasaría si desarrollo v(a) aquí?
                [DT*c   ,DT*s   ,0],
                [-DT*s  , DT*c  ,0],
                [0      ,0      ,DT],
                
            ])
        Q = G @ np.diag([ACCEL_NOISE**2, ACCEL_NOISE**2, GYRO_NOISE**2]) @ np.transpose(G)
        P_pred = np.zeros((5,5))
        P_pred = F @ P_est[:,:,i-1] @ np.transpose(F) + Q 

        x_est = x_pred
        p_est[:,i] = x_est[0:2] # Remind slices x:y doesn't include y
        v_est[:,i] = x_est[2:4]
        theta_est[i] = x_est[4]
        P_est[:,:,i] = P_pred

        ### Update
        ## vision
        #innov = vision[:,i] - p_pred[:,i]
        #S_vision = H_vision @ P_pred @ np.transpose(H_vision) + R_vision
        #K_f = P_pred @ np.transpose(H_vision) @ np.linalg.inv(S_vision)
        #x_est = x_est + K_f @ innov 
        #p_est[:,i] = x_est[0:2] # Remind slices x:y doesn't include y
        #v_est[:,i] = x_est[2:4]
        #theta_est[i] = x_est[4]
        #p_est[:,i] = x_est[1:2]
        #P[:,:,i] = P_pred + K_f @ H_vision @ P_pred

        ## gps
        innov = gps[:,i] - p_est[:,i]
        S_gps = H_gps @ P_est[:,:,i] @ np.transpose(H_gps) + R_gps
        K_f = P_est[:,:,i] @ np.transpose(H_gps) @ np.linalg.inv(S_gps)
        x_est = x_est + K_f @ innov 
        p_est[:,i] = x_est[0:2] # Remind slices x:y doesn't include y
        v_est[:,i] = x_est[2:4]
        theta_est[i] = x_est[4]
        P_est[:,:,i] = P_est[:,:,i] - K_f @ H_gps @ P_est[:,:,i]
    

    # Plot results
    fig, ax = plt.subplots()
    ax.set_title('X position versus time')
    ax.plot(t, p[0,:], label='P groundtruth')
    if DRAW_ESTIMATED:
        ax.plot(t, p_est[0,:], label='P estimated')
        ax.plot(t, P_est[0,0,:],label='error estimated')
    plt.xlabel('t (s)')
    plt.ylabel('$P_x$ (m)')
    ax.legend()
    plt.savefig(IMAGE_FOLDER + 'x_t.' + IMAGE_EXTENSION)

    fig, ax = plt.subplots()
    ax.set_title('Y position versus time')
    ax.plot(t, p[1,:], label='P groundtruth')
    if DRAW_ESTIMATED:
        ax.plot(t, p_est[1,:], label='P estimated')
        ax.plot(t, P_est[1,1,:],label='error estimated')
    plt.xlabel('t (s)')
    plt.ylabel('$P_y$ (m)')
    ax.legend()
    plt.savefig(IMAGE_FOLDER + 'y_t.' + IMAGE_EXTENSION)

    fig, ax = plt.subplots()
    ax.set_title('Velocity versus time')
    ax.plot(t, v[0,:],color='tab:red', label='$V_x$ groundtruth', linestyle='--')
    ax.plot(t, v[1,:],color='tab:blue', label='$V_y$ groundtruth', linestyle='--')
    if DRAW_ESTIMATED:
        ax.plot(t, v_est[0,:],color='tab:red', label='$V_x$ estimated')
        ax.plot(t, v_est[1,:],color='tab:blue', label='$V_y$ estimated')
        ax.plot(t, P_est[2,2,:],label='error estimated $V_x$')
        ax.plot(t, P_est[3,3,:],label='error estimated $V_y$')
    plt.xlabel('t (s)')
    plt.ylabel('$V$ (m/s)')
    ax.legend()
    plt.savefig(IMAGE_FOLDER + 'V.' + IMAGE_EXTENSION)

    fig, ax = plt.subplots()
    ax.set_title('Tilt versus time')
    ax.plot(t, theta, label='groundtruth')
    if DRAW_ESTIMATED:
        ax.plot(t, theta_est, label='estimated')
        ax.plot(t, P_est[4,4,:],label='error estimated')
    plt.xlabel('t (s)')
    plt.ylabel(r'$\theta$ (rad)')
    ax.legend()
    plt.savefig(IMAGE_FOLDER + 'theta.' + IMAGE_EXTENSION)

    fig, ax = plt.subplots()
    ax.set_title('Y versus X')
    ax.plot(p[0,:],p[1,:], label='groundtruth')
    if DRAW_ESTIMATED:
        ax.plot(p_est[0,:],p_est[1,:], label='P estimated')
    plt.xlabel('$P_x$ (m)')
    plt.ylabel('$P_y$ (m)')
    ax.legend()
    ax.set_aspect('equal')
    plt.savefig(IMAGE_FOLDER + 'tray.' + IMAGE_EXTENSION)

    # Sensors
    fig, ax = plt.subplots()
    ax.set_title('Acelerometer')
    ax.plot(t, accel_gt[0,:],   color='tab:red',    label='$a_x$ groundtruth', linestyle='--')
    ax.plot(t, accel_gt[1,:],   color='tab:blue',   label='$a_y$ groundtruth', linestyle='--')
    ax.plot(t, accel[0,:],      color='tab:red',    label='$a_x$ measure')
    ax.plot(t, accel[1,:],      color='tab:blue',   label='$a_y$ measure')
    plt.xlabel('t (s)')
    plt.ylabel('a (m/s)')
    ax.legend()
    plt.savefig(IMAGE_FOLDER + 'accel.' + IMAGE_EXTENSION)

    fig, ax = plt.subplots()
    ax.set_title(r'Gyro ($\omega$)')
    ax.plot(t, thetad,label='groundtruth')
    ax.plot(t, gyro,  label='measure')
    plt.xlabel('t (s)')
    plt.ylabel(r'$\omega$ (rad/s)')
    ax.legend()
    plt.savefig(IMAGE_FOLDER + 'gyro.' + IMAGE_EXTENSION)

    fig, ax = plt.subplots()
    ax.set_title('GPS')
    ax.plot(p[0,:],p[1,:],label='groundtruth')
    ax.plot(gps[0,:],gps[1,:],  label='measure', linestyle=" ", marker="x")
    plt.xlabel('$P_x$ (m)')
    plt.ylabel('$P_y$ (m)')
    ax.legend()
    ax.set_aspect('equal')
    plt.savefig(IMAGE_FOLDER + 'gps.' + IMAGE_EXTENSION)

    fig, ax = plt.subplots()
    ax.set_title('Elementos diagonales de la matriz de covarianzas')
    ax.plot(t,P_est[0,0,:],label='$P_x$')
    ax.plot(t,P_est[1,1,:],label='$P_y$')
    ax.plot(t,P_est[2,2,:],label='$V_x$')
    ax.plot(t,P_est[3,3,:],label='$V_y$')
    ax.plot(t,P_est[4,4,:],label=r'$\theta$')
    plt.xlabel('$t$ (s)')
    plt.ylabel('m,m,m/s,m/s,rad')
    ax.legend()
    plt.savefig(IMAGE_FOLDER + 'P_est_diag.' + IMAGE_EXTENSION)

    fig, ax = plt.subplots()
    ax.set_title('Matriz de covarianzas')
    # Parece que es diagonal
    ax.plot(t,P_est[0,1,:],label='$P_{est}$[0,1]')
    ax.plot(t,P_est[0,2,:],label='$P_{est}$[0,2]')
    ax.plot(t,P_est[0,3,:],label='$P_{est}$[0,3]')
    ax.plot(t,P_est[0,4,:],label='$P_{est}$[0,4]')
    ax.plot(t,P_est[1,2,:],label='$P_{est}$[1,2]')
    ax.plot(t,P_est[1,3,:],label='$P_{est}$[1,3]')
    ax.plot(t,P_est[1,4,:],label='$P_{est}$[1,4]')
    ax.plot(t,P_est[2,3,:],label='$P_{est}$[2,3]')
    ax.plot(t,P_est[2,4,:],label='$P_{est}$[2,4]')
    ax.plot(t,P_est[3,4,:],label='$P_{est}$[3,4]')
    ax.plot(t,P_est[0,0,:],label='$P_x$', linestyle="--")
    ax.plot(t,P_est[1,1,:],label='$P_y$', linestyle="--")
    ax.plot(t,P_est[2,2,:],label='$V_x$', linestyle="--")
    ax.plot(t,P_est[3,3,:],label='$V_y$', linestyle="--")
    plt.xlabel('$t$ (s)')
    ax.legend()
    plt.savefig(IMAGE_FOLDER + 'P_est' + IMAGE_EXTENSION)


    plt.show()

    draw_animation(p[0,:],p[1,:],theta)

if __name__=="__main__":
    main()