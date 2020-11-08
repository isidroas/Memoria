void VisionClass::InvertPose(Eigen::Vector3d &pos, Eigen::Vector3d &eul, Vec3d &rvec, Vec3d &tvec){
    /* @brief Invierte la posición y la rotación. También corrige la posición de la cámara con respecto al UAV
     * @param pos   posición del uav/cámara con respecto al marcador
     * @param eul   orientación del uav con respecto al marcador. El orden de los elementos son 0: roll, 1: pitch, 2: yaw
     * @param rvec  Vector de rotación del marcador con respecto a los ejes de la cámara
     * @param tvec  Vector de translación del marcador con respecto a los ejes de la cámara
     */

    Eigen::Vector3d     pos_marker_in_camera(tvec[0],tvec[1],tvec[2]);
    
    // Transformación de vector de rotación a matriz de rotación
    cv::Mat                     rot_mat;
    Eigen::Matrix3d             rot_mat_marker_from_camera; 
    Rodrigues(rvec,rot_mat);
    cv::cv2eigen(rot_mat, rot_mat_marker_from_camera);

    // La inversa de una matriz de rotación es igual a su traspuesta
    Eigen::Matrix3d     rot_mat_camera_from_marker = rot_mat_marker_from_camera.transpose() ; 

    // Se obtiene la posición del marcador en unos ejes paralelos al marcador centrados en la cámara
    Eigen::Vector3d     pos_marker_in_marker_axis = rot_mat_camera_from_marker*pos_marker_in_camera;

    // Si queremos que la posición esté centrada en el marcador y no en la cámara, es necesario negarla
    pos = -pos_marker_in_marker_axis;
    
    // Aquí debemos de tener en cuenta la rotación de la cámara con respecto al uav. Esta es de 180º alrededor del eje z
    // (de la cámara o del uav, da igual, por tanto da igual postmultiplicar que premultiplicar)
    Eigen::Matrix3d             rot_mat_camera_from_uav;
    rot_mat_camera_from_uav     << -1,   0,   0,
                                    0,  -1,   0,
                                    0,   0,   1;
    Eigen::Matrix3d             rot_mat_marker_from_uav = rot_mat_marker_from_camera * rot_mat_camera_from_uav; 

    // Se obtiene la orientación del uav visto desde el marcador
    Eigen::Matrix3d             rot_mat_uav_from_marker = rot_mat_marker_from_uav.transpose() ; 

    // Se obtiene los ángulos de Tait–Bryan en el orden Z-Y-X (ángulos de euler)
    eul = rotationMatrixToEulerAngles(rot_mat_uav_from_marker);
}
