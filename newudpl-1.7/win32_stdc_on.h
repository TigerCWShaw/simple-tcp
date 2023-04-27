/** def/undef _STDC_ macro *******************************************
 * This is needed because header file in MS VC++ and Borland C++
 * will eliminate extended functions and keywords when _STDC_ is set.
 */
#ifdef WIN32
#define __STDC__ 1
#endif
