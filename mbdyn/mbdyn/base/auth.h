/* 
 * MBDyn (C) is a multibody analysis code. 
 * http://www.mbdyn.org
 *
 * Copyright (C) 1996-2000
 *
 * Pierangelo Masarati	<masarati@aero.polimi.it>
 * Paolo Mantegazza	<mantegazza@aero.polimi.it>
 *
 * Dipartimento di Ingegneria Aerospaziale - Politecnico di Milano
 * via La Masa, 34 - 20156 Milano, Italy
 * http://www.aero.polimi.it
 *
 * Changing this copyright notice is forbidden.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation (version 2 of the License).
 * 
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */

#ifndef AUTH_H
#define AUTH_H

#include <unistd.h>
#include <string.h>

class AuthMethod {
 public:
   enum AuthRes {
      AUTH_UNKNOWN,
      AUTH_OK,
      AUTH_FAIL,
      AUTH_ERR
   };      
   
 public:   
   virtual ~AuthMethod(void) {};
   
   virtual AuthMethod::AuthRes 
     Auth(const char *user, const char *cred) const = 0;
};


/* NoAuth - begin */

/* always OK */

class NoAuth : public AuthMethod {
 public:
   AuthMethod::AuthRes 
     Auth(const char * /* user */ , const char * /* cred */ ) const;
};

/* NoAuth - end */


/* PasswordAuth - begin */

/* simple password comparison */

#ifdef HAVE_CRYPT

class PasswordAuth: public AuthMethod {
 protected:
   char User[9];
   char Cred[14];
   
 public:
   PasswordAuth(const char *u, const char *c);
   
   AuthMethod::AuthRes
     Auth(const char *user, const char *cred) const;
};

#endif /* HAVE_CRYPT */

/* PasswordAuth - end */


/* PAM_Auth - begin */

/* pam authentication */

#ifdef USE_PAM

class PAM_Auth: public AuthMethod {
 protected:
   char* User;
   
 public:
   PAM_Auth(const char *u = NULL);
   
   AuthMethod::AuthRes
     Auth(const char *user, const char *cred) const;
};

#endif /* USE_PAM */

/* PAM_Auth - end */


class DataManager;
class MBDynParser;

extern AuthMethod* ReadAuthMethod(DataManager* pDM,
				  MBDynParser& HP);

#endif
